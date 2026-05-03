"""Strategy agent — RAG Smogon + razonamiento competitivo ligero.

Doble fuente:
1. ``pokedex_strategy`` collection en Qdrant (chunks de análisis Smogon).
2. ``CoverageAnalyzer`` del dominio cuando el contexto incluye un ``Team``.

Haiku sintetiza ambas vías en una respuesta táctica con citas.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agents.base import AgentInput, AgentResponse, BaseAgent
from domain.team.entities import Team
from domain.team.services import CoverageAnalyzer
from infrastructure.llm_client import (
    LLMClient,
    LLMOptions,
    LLMRole,
    get_llm_client,
)
from infrastructure.observability import traced
from infrastructure.settings import get_settings
from infrastructure.vector_store import VectorStore
from shared.logging import get_logger
from shared.types import Source

log = get_logger(__name__)


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_strategy_llm_json(text: str) -> dict[str, object] | None:
    """Extrae objeto JSON del texto del modelo (con o sin fence ```)."""
    cleaned = _strip_code_fence(text)
    try:
        out = json.loads(cleaned)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        out = json.loads(m.group(0))
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        return None


def _markdown_from_strategy_payload(data: dict[str, object]) -> str:
    """Markdown con líneas `1. **Nombre**` para post-proceso en Synthesizer."""
    raw = data.get("teammates")
    teammates = raw if isinstance(raw, list) else []
    lines: list[str] = []
    n = 0
    for tm in teammates[:5]:
        if not isinstance(tm, dict):
            continue
        n += 1
        name = str(tm.get("name", "?"))
        role = str(tm.get("role", ""))
        lines.append(f"{n}. **{name}** — {role}")
        evs = tm.get("evs")
        if evs:
            lines.append(f"   EVs: {evs}")
    analysis = data.get("analysis")
    if analysis:
        lines.append("")
        lines.append(str(analysis))
    return "\n".join(lines) if lines else str(analysis or "Sin recomendaciones concretas.")


_STRATEGY_SYSTEM = """Eres un coach competitivo Pokémon (formato OU/VGC).
Usa el contexto [n] solo como referencia interna; la salida visible debe ser
**exclusivamente** un único objeto JSON válido (sin markdown, sin texto fuera del JSON):

{
  "teammates": [
    {"name": "Tyranitar", "role": "Physical Wall", "evs": "252 HP / 4 Atk / 252 SpD"},
    {"name": "Gyarados", "role": "Setup Sweeper", "evs": "252 Atk / 4 Def / 252 Spe"}
  ],
  "analysis": "Breve texto explicativo (misma lengua que la pregunta)."
}

Reglas:
- Incluye entre 3 y 5 objetos en "teammates" cuando la pregunta pida compañeros/teammates.
- Nombres de Pokémon en inglés canónico.
- Si no hay datos suficientes, "teammates": [] y "analysis" explicando el vacío.
"""


class StrategyAgent(BaseAgent):
    """Agent RAG con razonamiento competitivo."""

    name = "strategy_agent"

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        store: VectorStore | None = None,
        collection: str | None = None,
        top_k: int = 5,
    ) -> None:
        super().__init__(name=self.name)
        self._llm = llm or get_llm_client()
        self._store = store
        self._collection = collection or get_settings().qdrant_collection_strategy
        self._top_k = top_k

    @property
    def store(self) -> VectorStore:
        if self._store is None:
            self._store = VectorStore()
        return self._store

    @traced("strategy_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        # 1) Coverage si llega un Team en el contexto.
        team_block = self._maybe_team_block(agent_input)

        # 2) RAG sobre la colección strategy.
        hits_block, sources = self._maybe_rag_block(agent_input)

        if not team_block and not hits_block:
            return AgentResponse(
                agent=self.name,
                content=(
                    "No tengo aún corpus competitivo ingresado en Qdrant ni "
                    "un equipo en el contexto para analizar coberturas. "
                    "Pásame un `Team` o ingresa el corpus Smogon (FASE 2)."
                ),
                confidence=0.0,
                trace_id=agent_input.trace_id,
            )

        prompt = (
            f"## Pregunta\n{agent_input.query}\n\n"
            f"{team_block}\n{hits_block}\n\n"
            "Responde únicamente con el JSON descrito en el system prompt."
        ).strip()

        response = self._llm.complete(
            prompt,
            role=LLMRole.LIGHT,
            options=LLMOptions(
                max_tokens=220,
                temperature=0.2,
                system=_STRATEGY_SYSTEM,
            ),
        )

        parsed = _parse_strategy_llm_json(response.text)
        confidence = 0.85 if sources and team_block else (0.7 if sources or team_block else 0.4)
        if isinstance(parsed, dict):
            content = _markdown_from_strategy_payload(parsed)
            data: dict[str, Any] = {
                "rag_hits": len(sources),
                "team_analyzed": bool(team_block),
                "model": response.model,
                "teammates": parsed.get("teammates", []),
                "analysis": parsed.get("analysis", ""),
            }
        else:
            log.info("strategy_agent.json_parse_failed", snippet=response.text[:200])
            content = response.text.strip()
            data = {
                "rag_hits": len(sources),
                "team_analyzed": bool(team_block),
                "model": response.model,
                "parse_error": True,
            }

        return AgentResponse(
            agent=self.name,
            content=content,
            sources=sources,
            confidence=confidence,
            data=data,
            trace_id=agent_input.trace_id,
        )

    def execute(self, state: dict) -> dict:
        """Fallback graceful si Groq falla."""
        entities = state.get("entities", {}) or {}
        pokemon_name = entities.get("pokemon", "pikachu")
        if isinstance(pokemon_name, list):
            pokemon_name = pokemon_name[0] if pokemon_name else "pikachu"
        try:
            hits = self.store.search_text(
                collection=self._collection,
                query=str(pokemon_name),
                top_k=1,
            )
            if not hits:
                state["strategy_response"] = json.dumps({})
                return state
            state["strategy_response"] = json.dumps({
                "tier": hits[0].payload.get("tier", "Unknown")
            })
        except Exception as e:
            log.error(f"Strategy agent error: {e}")
            state["strategy_response"] = json.dumps({})
        return state

    # --- helpers ---------------------------------------------------------

    def _maybe_team_block(self, agent_input: AgentInput) -> str:
        team = agent_input.context.get("team")
        if not isinstance(team, Team):
            return ""
        report = CoverageAnalyzer.analyze(team)
        uncovered = ", ".join(t.value for t in report.uncovered_types) or "ninguno"
        quad = ", ".join(t.value for t in report.quad_weak_types) or "ninguno"
        return (
            "## Análisis de coberturas (CoverageAnalyzer)\n"
            f"- Equipo: **{team.name}** ({len(team.members)} miembros)\n"
            f"- Tipos sin cobertura ofensiva: {uncovered}\n"
            f"- Tipos con debilidad ×4 en el equipo: {quad}\n"
        )

    def _maybe_rag_block(
        self, agent_input: AgentInput
    ) -> tuple[str, list[Source]]:
        try:
            rag_query = agent_input.query
            hint = agent_input.context.get("pokemon_hint")
            if hint:
                h = str(hint).strip().lower()
                if h and h not in rag_query.lower():
                    rag_query = f"{h} OU teammates synergy {rag_query}"
            hits = self.store.search_text(
                collection=self._collection,
                query=rag_query,
                top_k=self._top_k,
            )
        except Exception as exc:
            log.info(
                "strategy_agent.no_collection", error=str(exc), collection=self._collection
            )
            return "", []

        if not hits:
            return "", []

        blocks: list[str] = []
        sources: list[Source] = []
        for i, hit in enumerate(hits, start=1):
            payload = hit.payload
            title = str(payload.get("title", f"chunk-{hit.id}"))
            url = payload.get("url")
            snippet = str(payload.get("text", payload.get("snippet", "")))[:600]
            blocks.append(f"[{i}] {title}\n{snippet}")
            sources.append(
                Source(
                    id=f"strategy:{hit.id}",
                    title=title,
                    url=url,
                    snippet=snippet[:300],
                    kind="smogon" if url and "smogon" in url else "strategy",
                )
            )
        return "## Contexto Smogon\n" + "\n\n".join(blocks), sources


__all__ = ["StrategyAgent"]
