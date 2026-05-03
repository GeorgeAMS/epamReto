"""Lore agent — RAG sobre Bulbapedia/PDFs.

Pipeline:
1. Embebe la query con OpenAI (o fallback determinístico) → vector.
2. Busca en la colección Qdrant ``pokedex_lore`` los top-k chunks.
3. Construye un prompt con el contexto recuperado + cita por payload.
4. Haiku sintetiza una respuesta y devuelve ``AgentResponse`` con
   ``sources`` apuntando a las URLs/títulos del payload.

Cuando Qdrant no tiene la colección o está vacía (común en dev sin ingest),
respondemos honestamente con ``confidence=0.0`` para que el verifier marque
la respuesta como ``CONTRADICTION`` y la UI lo refleje.
"""

from __future__ import annotations

import json

from agents.base import AgentInput, AgentResponse, BaseAgent
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


_LORE_SYSTEM = """Eres un experto en lore Pokémon (anime, manga, regiones, equipos rivales).
- Cita cada hecho usando los marcadores [1], [2] que aparecen en el contexto.
- Si el contexto no contiene la respuesta, dilo explícitamente.
- Mantén respuestas en 2–6 párrafos.
"""


class LoreAgent(BaseAgent):
    """Agent RAG sobre la colección ``pokedex_lore``."""

    name = "lore_agent"

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
        self._collection = collection or get_settings().qdrant_collection_lore
        self._top_k = top_k

    @property
    def store(self) -> VectorStore:
        # Lazy: solo conectamos a Qdrant cuando hace falta (los tests pueden
        # inyectar un store fake o saltar la conexión usando is_offline-style).
        if self._store is None:
            self._store = VectorStore()
        return self._store

    @traced("lore_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        try:
            hits = self.store.search_text(
                collection=self._collection,
                query=agent_input.query,
                top_k=self._top_k,
            )
        except Exception as exc:
            # Qdrant offline / colección no creada / red caída → degradamos
            # con honestidad en vez de tirar la query completa.
            log.info("lore_agent.no_collection", error=str(exc), collection=self._collection)
            return self._empty_response(
                agent_input,
                reason=f"colección {self._collection} no disponible ({type(exc).__name__})",
            )

        if not hits:
            return self._empty_response(agent_input, reason="sin matches en lore")

        context_blocks: list[str] = []
        sources: list[Source] = []
        for i, hit in enumerate(hits, start=1):
            payload = hit.payload
            title = str(payload.get("title", f"chunk-{hit.id}"))
            url = payload.get("url")
            snippet = str(payload.get("text", payload.get("snippet", "")))[:600]
            context_blocks.append(f"[{i}] {title}\n{snippet}")
            sources.append(
                Source(
                    id=f"lore:{hit.id}",
                    title=title,
                    url=url,
                    snippet=snippet[:300],
                    kind="bulbapedia" if url and "bulbapedia" in url else "lore",
                )
            )

        prompt = (
            f"## Pregunta\n{agent_input.query}\n\n"
            f"## Contexto recuperado\n" + "\n\n".join(context_blocks) + "\n\n"
            "Responde con citas [n] referenciando el contexto."
        )
        response = self._llm.complete(
            prompt,
            role=LLMRole.LIGHT,
            options=LLMOptions(max_tokens=320, temperature=0.2, system=_LORE_SYSTEM),
        )

        confidence = 0.85 if len(sources) >= 2 else 0.6
        return AgentResponse(
            agent=self.name,
            content=response.text,
            sources=sources,
            confidence=confidence,
            data={"hits": len(hits), "model": response.model},
            trace_id=agent_input.trace_id,
        )

    def execute(self, state: dict) -> dict:
        """Busca lore rápido en Qdrant para síntesis conversacional."""
        entities = state.get("entities", {}) or {}
        pokemon_name = entities.get("pokemon", "pikachu")
        if isinstance(pokemon_name, list):
            pokemon_name = pokemon_name[0] if pokemon_name else "pikachu"
        if not pokemon_name:
            state["lore_response"] = json.dumps({})
            return state
        try:
            hits = self.store.search_text(
                collection=self._collection,
                query=str(pokemon_name),
                top_k=2,
            )
            if not hits:
                state["lore_response"] = json.dumps({})
                return state
            top = hits[0].payload
            context = str(top.get("text", top.get("snippet", "")))[:400]
            state["lore_response"] = json.dumps(
                {
                    "lore": context,
                    "source": top.get("url", "Bulbapedia"),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.error(f"Lore agent error: {e}")
            state["lore_response"] = json.dumps({})
        return state

    def _empty_response(self, agent_input: AgentInput, *, reason: str) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            content=(
                "No encontré información de lore relevante en la base de "
                f"conocimiento ({reason}). Cuando ingestemos Bulbapedia "
                "(FASE 2 — `bulbapedia_scraper`) este agente devolverá citas reales."
            ),
            confidence=0.0,
            trace_id=agent_input.trace_id,
        )


__all__ = ["LoreAgent"]
