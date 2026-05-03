"""Lore agent — RAG sobre Bulbapedia/PDFs.

Pipeline:
1. Embebe la query con OpenAI (o fallback determinístico) → vector.
2. Busca en la colección Qdrant ``pokedex_lore`` los top-k chunks.
3. Construye un prompt con el contexto recuperado + cita por payload.
4. LLM sintetiza con reglas anti-alucinación (solo hechos del contexto).

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
from infrastructure.vector_store import SearchHit, VectorStore
from shared.logging import get_logger
from shared.types import Source

log = get_logger(__name__)

_ANIME_QUERY_HINTS: tuple[str, ...] = (
    "anime",
    "episodio",
    "episodios",
    "serie animada",
    "temporada",
    "opening",
    "ending",
    "doblaje",
    " ash",
    "ash ",
    "misty",
    "brock",
    "team rocket",
    "manga",
    "adventures",
    "journeys",
    "horizons",
    "alola",
    "galar",
    "kalos",
    "unova",
    "sinnoh",
    "johto",
    "kanto",
    "personaje",
    "historia del anime",
    "serie pokémon",
    "serie pokemon",
    "trama",
    "argumento",
)

_LORE_SYSTEM = """Eres un asistente de lore Pokémon con acceso SOLO al contexto numerado [1], [2], … que se te da (extractos de Bulbapedia u otras fuentes indexadas).

REGLAS OBLIGATORIAS (anime, manga, historia, personajes):
1. Solo afirma hechos que aparezcan de forma clara en algún bloque [n]. Cada afirmación importante debe llevar su cita [n].
2. NO inventes resultados de ligas, victorias, derrotas, episodios, diálogos, fechas, nombres de capítulos ni orden de temporadas si no constan en el contexto.
3. NO completes huecos con “lo típico del anime” o conocimiento general: si el contexto no lo dice, dilo explícitamente (“en el extracto indexado no consta…”).
4. Si la pregunta va de anime/manga y el contexto es solo ficha de una especie sin datos de serie, dilo y no rellenes con suposiciones.
5. Responde en el mismo idioma que el usuario; 2–6 párrafos; tono claro y neutral.
"""


def _wants_anime_corpus(query: str) -> bool:
    t = query.lower()
    return any(h in t for h in _ANIME_QUERY_HINTS)


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

    def _merge_hits(self, query: str, *, top_k: int | None = None) -> list[SearchHit]:
        """Prioriza chunks ``lore_topic=anime_manga`` cuando la pregunta huele a anime/manga."""
        k = self._top_k if top_k is None else top_k
        if not _wants_anime_corpus(query):
            return self.store.search_text(
                collection=self._collection,
                query=query,
                top_k=k,
            )

        want = max(k, 6)
        anime = self.store.search_text(
            collection=self._collection,
            query=query,
            top_k=want,
            filters={"lore_topic": "anime_manga"},
        )
        if len(anime) >= 2:
            return anime[:k]

        general = self.store.search_text(
            collection=self._collection,
            query=query,
            top_k=want,
        )
        seen: set[str] = set()
        merged: list[SearchHit] = []
        for h in (*anime, *general):
            url = str(h.payload.get("url") or "")
            key = url or str(h.id)
            if key in seen:
                continue
            seen.add(key)
            merged.append(h)
            if len(merged) >= k:
                break
        return merged

    @traced("lore_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        try:
            hits = self._merge_hits(agent_input.query)
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
            snippet = str(payload.get("text", payload.get("snippet", "")))[:900]
            context_blocks.append(f"[{i}] {title}\n{snippet}")
            topic = str(payload.get("lore_topic", "") or "")
            if url and "bulbapedia" in str(url) and topic == "anime_manga":
                kind = "bulbapedia_anime"
            elif url and "bulbapedia" in str(url):
                kind = "bulbapedia"
            else:
                kind = "lore"
            sources.append(
                Source(
                    id=f"lore:{hit.id}",
                    title=title,
                    url=str(url) if url else None,
                    snippet=snippet[:300],
                    kind=kind,
                )
            )

        prompt = (
            f"## Pregunta\n{agent_input.query}\n\n"
            f"## Contexto recuperado (única fuente de hechos)\n"
            + "\n\n".join(context_blocks)
            + "\n\n"
            "Responde usando solo información anterior; cita con [n]. "
            "Si algo no está en esos extractos, no lo afirmes."
        )
        response = self._llm.complete(
            prompt,
            role=LLMRole.LIGHT,
            options=LLMOptions(max_tokens=480, temperature=0.1, system=_LORE_SYSTEM),
        )

        confidence = 0.82 if len(sources) >= 2 else 0.55
        if _wants_anime_corpus(agent_input.query) and not any(
            h.payload.get("lore_topic") == "anime_manga" for h in hits
        ):
            confidence = min(confidence, 0.42)

        return AgentResponse(
            agent=self.name,
            content=response.text,
            sources=sources,
            confidence=confidence,
            data={"hits": len(hits), "model": response.model},
            trace_id=agent_input.trace_id,
        )

    def execute(self, state: dict) -> dict:
        """Busca lore en Qdrant para síntesis conversacional (usa la pregunta + Pokémon)."""
        entities = state.get("entities", {}) or {}
        pokemon_raw = entities.get("pokemon", "")
        if isinstance(pokemon_raw, list):
            pokemon_name = pokemon_raw[0] if pokemon_raw else ""
        else:
            pokemon_name = str(pokemon_raw or "").strip()

        query = str(state.get("query", "") or "").strip()
        search_q = query if query else pokemon_name
        if not search_q:
            state["lore_response"] = json.dumps({})
            return state

        if pokemon_name and query and pokemon_name.lower() not in query.lower():
            search_q = f"{query}\n{pokemon_name}"

        try:
            hits = self._merge_hits(search_q, top_k=5)
            if not hits:
                state["lore_response"] = json.dumps({})
                return state
            parts: list[str] = []
            for h in hits[:3]:
                top = h.payload
                t = str(top.get("text", top.get("snippet", "")))[:650]
                title = str(top.get("title", "fuente"))
                parts.append(f"## {title}\n{t}")
            lore_text = "\n\n".join(parts)
            main_url = hits[0].payload.get("url", "Bulbapedia")
            state["lore_response"] = json.dumps(
                {
                    "lore": lore_text[:2200],
                    "source": main_url,
                    "anime_indexed": any(h.payload.get("lore_topic") == "anime_manga" for h in hits),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.error("lore_agent.execute_error", error=str(e))
            state["lore_response"] = json.dumps({})
        return state

    def _empty_response(self, agent_input: AgentInput, *, reason: str) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            content=(
                "No encontré información de lore relevante en la base de "
                f"conocimiento ({reason}). Ejecuta ingesta Bulbapedia (especies y/o "
                "`anime-manga` + `bulbapedia_ingest --from-disk`) para citas reales."
            ),
            confidence=0.0,
            trace_id=agent_input.trace_id,
        )


__all__ = ["LoreAgent"]
