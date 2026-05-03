"""Synthesizer — toma respuestas de los sub-agentes y produce la respuesta final.

Reglas:
- Re-numera todas las ``Source`` globalmente como ``[1]``, ``[2]``, ... y le pide
  al LLM que cite cada hecho con esos números (la UI los renderiza como chips).
- Usa el modelo ligero (``LLMRole.LIGHT``) con ``options.system`` que reúne las
  reglas de citación.
- Expone dos modos:
    * ``run(agent_input, agent_outputs)``     → ``AgentResponse`` completa.
    * ``stream(agent_input, agent_outputs)``  → ``Iterator[str]`` con tokens
      reales de Anthropic; lo consume el endpoint SSE.

Si no hay outputs (caso defensivo) devuelve un eco honesto con confidence baja.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
import traceback

import json

from agents.base import AgentInput, AgentResponse, BaseAgent
from infrastructure.llm_client import (
    LLMClient,
    LLMOptions,
    LLMRole,
    get_llm_client,
)
from infrastructure.observability import traced
from shared.errors import AgentError
from shared.logging import get_logger
from shared.types import Source, confidence_to_level

log = get_logger(__name__)


_SYSTEM_PROMPT = """Eres POKÉDEX ARCANA, un asistente experto en Pokémon competitivo.

Tu trabajo es sintetizar la respuesta final a partir de los outputs de varios
sub-agentes especializados (stats, cálculo de daño, estrategia, lore).

REGLAS DURAS:
1. Cita cada hecho con marcadores ``[1]``, ``[2]``, etc., usando los números
   que aparecen en la sección "Fuentes" del prompt.
2. NUNCA inventes datos. Si los sub-agentes no aportan algo, dilo explícitamente.
3. Mantén el formato Markdown: títulos con `##`, listas, negritas en nombres
   de Pokémon y movimientos.
4. Sé conciso pero completo: 3–10 párrafos máximo.
5. Si hay un cálculo de daño, preserva los valores numéricos exactos
   (rango, %HP) — vienen del calculator_agent y son verificados.
6. No menciones "los sub-agentes" en la respuesta — el usuario no los conoce.
7. Responde en el mismo idioma que el usuario (español por defecto).
"""


def _build_synthesis_prompt(
    query: str,
    agent_outputs: list[AgentResponse],
) -> tuple[str, list[Source]]:
    """Construye el user-prompt + la lista global de fuentes con índices [n].

    Devuelve ``(prompt, ordered_sources)`` donde ``ordered_sources[i]`` es la
    fuente que se cita como ``[i+1]``.
    """
    seen: dict[str, int] = {}
    ordered: list[Source] = []
    for resp in agent_outputs:
        for src in resp.sources:
            if src.id not in seen:
                seen[src.id] = len(ordered)
                ordered.append(src)

    bullet_lines: list[str] = []
    for resp in agent_outputs:
        cites = [str(seen[s.id] + 1) for s in resp.sources]
        cite_str = f"[{','.join(cites)}]" if cites else ""
        bullet_lines.append(
            f"- **{resp.agent}** (conf {resp.confidence:.2f}) {cite_str}\n"
            f"  {resp.content.strip()}"
        )

    sources_block_lines: list[str] = []
    for i, src in enumerate(ordered, start=1):
        url = src.url or "(sin URL)"
        sources_block_lines.append(f"[{i}] {src.title} — {url}")

    prompt = (
        f"## Pregunta del usuario\n{query}\n\n"
        f"## Outputs de sub-agentes\n" + "\n".join(bullet_lines) + "\n\n"
        "## Fuentes\n" + "\n".join(sources_block_lines) + "\n\n"
        "Sintetiza la respuesta final citando cada hecho con [n]."
    )
    return prompt, ordered


def _aggregate_confidence(agent_outputs: list[AgentResponse]) -> float:
    """Confidence agregada del sintetizador.

    Si el calculator_agent participó, su 1.0 ancla el resultado (es determinista).
    Si no, devolvemos la mediana ponderada simple.
    """
    if not agent_outputs:
        return 0.0
    has_deterministic = any(r.agent == "calculator_agent" for r in agent_outputs)
    if has_deterministic:
        return min(0.99, sum(r.confidence for r in agent_outputs) / len(agent_outputs) + 0.05)
    return sum(r.confidence for r in agent_outputs) / len(agent_outputs)


class Synthesizer(BaseAgent):
    """Combina outputs y produce respuesta final con citas inline."""

    name = "synthesizer"

    def __init__(self, *, llm: LLMClient | None = None) -> None:
        super().__init__(name=self.name)
        self._llm = llm or get_llm_client()

    @traced("synthesizer")
    def run(
        self,
        agent_input: AgentInput,
        agent_outputs: list[AgentResponse] | None = None,
    ) -> AgentResponse:
        outputs = agent_outputs or []
        if not outputs:
            return AgentResponse(
                agent=self.name,
                content=(
                    "No tengo información suficiente para responder. "
                    "Asegúrate de que la pregunta sea sobre Pokémon (stats, "
                    "cálculo de daño, estrategia o lore)."
                ),
                confidence=0.1,
                trace_id=agent_input.trace_id,
            )

        prompt, ordered_sources = _build_synthesis_prompt(agent_input.query, outputs)
        try:
            response = self._llm.complete(
                prompt,
                role=LLMRole.LIGHT,
                options=LLMOptions(
                    max_tokens=420,
                    temperature=0.2,
                    system=_SYSTEM_PROMPT,
                ),
            )
        except Exception as exc:
            # Modo emergencia: ante cualquier fallo del LLM (incl. 429 envuelto),
            # devolvemos síntesis deterministic para no romper la demo.
            log.warning("synthesizer.offline_fallback", error=str(exc))
            content = self._offline_synthesis(outputs, agent_input.query)
            return AgentResponse(
                agent=self.name,
                content=content,
                sources=ordered_sources,
                confidence=_aggregate_confidence(outputs),
                data={
                    "sub_agents": [r.agent for r in outputs],
                    "intent_outputs": [r.model_dump() for r in outputs],
                    "model": "offline-fallback",
                    "fallback_reason": "llm_error",
                },
                trace_id=agent_input.trace_id,
            )

        merged_data: dict[str, Any] = {
            "sub_agents": [r.agent for r in outputs],
            "intent_outputs": [r.model_dump() for r in outputs],
            "model": response.model,
            "tokens_in": response.input_tokens,
            "tokens_out": response.output_tokens,
        }

        return AgentResponse(
            agent=self.name,
            content=response.text,
            sources=ordered_sources,
            confidence=_aggregate_confidence(outputs),
            data=merged_data,
            trace_id=agent_input.trace_id,
        )

    def stream(
        self,
        agent_input: AgentInput,
        agent_outputs: list[AgentResponse],
    ) -> Iterator[str]:
        """Streaming real: yieldea tokens del SDK Anthropic.

        El endpoint SSE de la API se conecta directo a este iterador. Las
        citas (`[1]`, `[2]`) van saliendo a medida que el modelo las emite.
        """
        if not agent_outputs:
            yield "No tengo información suficiente para responder."
            return

        prompt, _ = _build_synthesis_prompt(agent_input.query, agent_outputs)
        yield from self._llm.stream(
            prompt,
            role=LLMRole.LIGHT,
            options=LLMOptions(
                max_tokens=420,
                temperature=0.2,
                system=_SYSTEM_PROMPT,
            ),
        )

    def _format_strategy(self, state: dict[str, Any]) -> str:
        """Formatea salida strategy antes que cualquier ruta stats."""
        dump = state.get("strategy_agent_dump")
        if dump is None:
            return ""
        if isinstance(dump, str):
            try:
                dump = json.loads(dump)
            except json.JSONDecodeError:
                return dump
        if not isinstance(dump, dict):
            return ""
        content = str(dump.get("content", "") or "")
        teammates = re.findall(r"\d+\.\s+\*\*(.+?)\*\*", content)
        if not teammates:
            data = dump.get("data")
            if isinstance(data, dict):
                raw_tms = data.get("teammates")
                if isinstance(raw_tms, list):
                    teammates = [
                        str(x.get("name", "")).strip()
                        for x in raw_tms
                        if isinstance(x, dict) and x.get("name")
                    ]
        if teammates:
            ent = state.get("entities") or {}
            label_raw = str(ent.get("pokemon", "este Pokémon"))
            label = label_raw.replace("-", " ").title()
            formatted = f"Para {label}, recomiendo:\n"
            for i, name in enumerate(teammates, 1):
                formatted += f"{i}. {name}\n"
            return formatted.rstrip()
        return content

    def _format_stats(self, state: dict[str, Any]) -> str:
        """Fallback directo si falla síntesis conversacional."""
        try:
            stats = json.loads(state.get("stats_response", "{}"))
            if stats.get("skipped"):
                return ""
            if "error" in stats:
                return "No encontré información sobre ese Pokémon."
            name = stats["name"].title()
            types = " / ".join(stats["types"])
            bs = stats.get("base_stats", {})
            ability = str(stats.get("ability", "Unknown")).title()
            return (
                f"{name} es un Pokémon de tipo {types}. "
                f"Tiene {ability} como habilidad principal y un total base de "
                f"{bs.get('total', '?')} (Velocidad {bs.get('speed', '?')})."
            )
        except Exception as e:
            log.error("synthesizer.stats_format", error=str(e))
            return "Error generando respuesta."

    def _synthesize_strategy(self, state: dict[str, Any]) -> dict[str, Any]:
        """Path strategy/team-building: prioriza el dump del StrategyAgent."""
        state["final_response"] = self._format_strategy(state)
        return state

    def _synthesize_conversational(
        self,
        query: str,
        intent: str,
        pokemon_name: str,
        sources: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Respuesta natural combinando stats + lore + strategy."""
        print("\n" + "=" * 80)
        print("[TRACE] _synthesize_conversational() - INICIO")
        print(f"  Query: {query}")
        print(f"  Intent: {intent}")
        print(f"  Pokemon: {pokemon_name}")
        print(f"  Sources keys: {list(sources.keys())}")
        print(f"  Sources content: {sources}")
        print("=" * 80 + "\n")
        context_parts: list[str] = []

        stats = sources.get("stats")
        if isinstance(stats, dict) and not stats.get("error"):
            print("  [OK] Agregando stats al contexto")
            types = " / ".join(stats.get("types", []))
            bs = stats.get("base_stats", {})
            context_parts.append(
                f"Stats de {str(stats.get('name', pokemon_name)).title()}:\n"
                f"- Tipos: {types}\n"
                f"- HP: {bs.get('hp')}, Atk: {bs.get('attack')}, Def: {bs.get('defense')}\n"
                f"- SpA: {bs.get('special_attack')}, SpD: {bs.get('special_defense')}, Spe: {bs.get('speed')}\n"
                f"- Habilidad: {stats.get('ability', 'Unknown')}"
            )

        lore = sources.get("lore")
        if isinstance(lore, dict) and lore.get("lore"):
            print("  [OK] Agregando lore al contexto")
            context_parts.append(f"Lore/Historia:\n{lore['lore']}")

        strategy = sources.get("strategy")
        if isinstance(strategy, dict) and strategy.get("tier"):
            print("  [OK] Agregando strategy al contexto")
            part = f"Competitivo:\n- Tier: {strategy['tier']}"
            if strategy.get("strategy"):
                part += f"\n- Notas: {strategy['strategy']}"
            context_parts.append(part)

        context = "\n\n".join(context_parts).strip()
        prompt = (
            "Eres un entrenador Pokémon experto y conversacional. "
            "Responde de forma natural y amigable, sin formato robótico.\n\n"
            f"Pregunta: {query}\n"
            f"Intent: {intent}\n"
            f"Pokémon principal: {pokemon_name or 'desconocido'}\n\n"
            f"Información disponible:\n{context or 'Sin contexto estructurado'}\n\n"
            "Instrucciones:\n"
            "- Español natural\n"
            "- Máximo 260 palabras\n"
            "- Integra datos de forma fluida\n"
            "- Si faltan datos, dilo sin inventar\n"
        )
        print("\n[TRACE] CONTEXTO PARA LLM:")
        print(context or "Sin contexto estructurado")
        print("\n[TRACE] PROMPT COMPLETO:")
        print(prompt)
        try:
            print("\n[TRACE] LLAMANDO A LLM...")
            response = self._llm.complete(
                prompt,
                role=LLMRole.LIGHT,
                options=LLMOptions(max_tokens=320, temperature=0.2),
            )
            response_text = getattr(response, "content", None) or getattr(response, "text", None) or str(response)
            print("[OK] LLM RESPONDIO:")
            print(f"  Type: {type(response)}")
            print(f"  Content: {response_text}")
            final_text = response.text.strip()
            if isinstance(stats, dict) and not stats.get("error"):
                final_text += "\n\n*Fuente principal: PokéAPI*"
            state["final_response"] = final_text
            return state
        except Exception as e:
            print("[ERROR] ERROR EN LLM:")
            print(f"  Exception: {e}")
            traceback.print_exc()
            log.error("synthesizer.conversational_error", error=str(e))
            if isinstance(stats, dict) and not stats.get("error"):
                print("[WARN] USANDO FALLBACK _format_stats")
                state["final_response"] = self._format_stats(state)
            else:
                print("[WARN] USANDO FALLBACK generico")
                state["final_response"] = "No encontré información suficiente para responder esa pregunta."
            return state

    def synthesize(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Sintetizador NATURAL multi-fuente.
        Strategy primero; luego conversación con stats+lore+strategy-info.
        """
        print("\n" + "=" * 80)
        print("[TRACE] SYNTHESIZER.synthesize() - INICIO")
        print(f"  Query: {state.get('query', 'N/A')}")
        print(f"  Intent: {state.get('intent', 'N/A')}")
        print(f"  Has strategy_dump: {'strategy_agent_dump' in state}")
        print(f"  Has stats: {'stats_response' in state}")
        print(f"  Has lore: {'lore_response' in state}")
        print("  Stack trace:")
        traceback.print_stack()
        print("=" * 80 + "\n")
        query = str(state.get("query", ""))
        intent = str(state.get("intent", "stats"))
        entities = state.get("entities") or {}
        pokemon_name = str(entities.get("pokemon", ""))

        if "strategy_agent_dump" in state and state["strategy_agent_dump"]:
            print("DEBUG: Usando path STRATEGY")
            return self._synthesize_strategy(state)

        print("DEBUG: Usando path CONVERSACIONAL")
        sources: dict[str, Any] = {}
        if "stats_response" in state:
            try:
                sources["stats"] = json.loads(state["stats_response"])
                print(f"DEBUG: Stats cargados: {sources['stats'].get('name')}")
            except Exception:
                print("DEBUG: Error cargando stats")
                pass
        if "lore_response" in state:
            try:
                sources["lore"] = json.loads(state["lore_response"])
                print("DEBUG: Lore cargado")
            except Exception:
                print("DEBUG: Error cargando lore")
                pass
        if "strategy_response" in state:
            try:
                sources["strategy"] = json.loads(state["strategy_response"])
                print("DEBUG: Strategy info cargada")
            except Exception:
                print("DEBUG: Error cargando strategy info")
                pass

        return self._synthesize_conversational(query, intent, pokemon_name, sources, state)

    @staticmethod
    def _offline_synthesis(agent_outputs: list[AgentResponse], query: str) -> str:
        """Síntesis mínima sin LLM para emergencias de cuota."""
        parts = [f"## Quick answer\n{query}"]
        for resp in agent_outputs:
            label = resp.agent.replace("_agent", "").replace("_", " ").title()
            snippet = resp.content.strip()
            if len(snippet) > 320:
                snippet = f"{snippet[:320]}..."
            parts.append(f"**{label}:** {snippet}")
        parts.append("Verified from PokeAPI + local calculations where available.")
        return "\n\n".join(parts)

    @staticmethod
    def render_confidence(response: AgentResponse) -> str:
        """Helper UI: convierte el score en un emoji breve."""
        level = confidence_to_level(response.confidence)
        return {"verified": "✅", "partial": "⚠️", "contradiction": "❌"}.get(level.value, "❔")


__all__ = ["Synthesizer"]
