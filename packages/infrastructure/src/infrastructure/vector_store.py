"""Wrapper minimalista sobre Qdrant.

El cliente expone:
- ``ensure_collection(name)``        — idempotente.
- ``upsert(...)``                    — vectores ya calculados.
- ``upsert_documents(...)``          — embebe + guarda en un solo paso.
- ``search(...)``                    — búsqueda por vector.
- ``hybrid_search(...)``             — búsqueda con filtros (mismo flow,
  separado para que el strategy_agent filtre por ``source=smogon`` etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from infrastructure.embeddings import GeminiEmbedder, OllamaEmbedder, get_embedder
from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SearchHit:
    """Resultado de una búsqueda semántica."""

    id: str
    score: float
    payload: dict[str, Any]


class VectorStore:
    _Embedder = GeminiEmbedder | OllamaEmbedder

    """Cliente Qdrant tipado.

    Cada documento ingresado debe portar al menos:
    - ``source`` (bulbapedia | smogon | pdf | dataset)
    - ``title`` y ``url`` para reconstruir la cita en la UI.
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        api_key: str | None = None,
        embedding_dim: int | None = None,
    ) -> None:
        settings = get_settings()
        self._client = QdrantClient(
            url=url or settings.qdrant_url,
            api_key=api_key or (settings.qdrant_api_key or None),
        )
        self.embedding_dim = embedding_dim or settings.embedding_dim

    def ensure_collection(self, name: str) -> None:
        """Crea la colección si no existe (idempotente)."""
        existing = {c.name for c in self._client.get_collections().collections}
        if name in existing:
            return
        log.info("qdrant.collection.create", name=name, dim=self.embedding_dim)
        self._client.create_collection(
            collection_name=name,
            vectors_config=qm.VectorParams(
                size=self.embedding_dim,
                distance=qm.Distance.COSINE,
            ),
        )

    def upsert(
        self,
        *,
        collection: str,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise InfrastructureError(
                "ids, vectors y payloads deben tener la misma longitud",
                details={"ids": len(ids), "vectors": len(vectors), "payloads": len(payloads)},
            )
        self._client.upsert(
            collection_name=collection,
            points=[
                qm.PointStruct(id=pid, vector=vec, payload=pl)
                for pid, vec, pl in zip(ids, vectors, payloads, strict=True)
            ],
        )

    def search(
        self,
        *,
        collection: str,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        flt = None
        if filters:
            flt = qm.Filter(
                must=[
                    qm.FieldCondition(key=k, match=qm.MatchValue(value=v))
                    for k, v in filters.items()
                ]
            )
        # qdrant-client ≥1.10 reemplazó `.search` por `.query_points`.
        response = self._client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
            query_filter=flt,
        )
        return [
            SearchHit(id=str(p.id), score=float(p.score), payload=dict(p.payload or {}))
            for p in response.points
        ]

    # --- Helpers de alto nivel ------------------------------------------

    def upsert_documents(
        self,
        *,
        collection: str,
        texts: list[str],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
        embedder: _Embedder | None = None,
    ) -> list[str]:
        """Embebe ``texts`` y los guarda en Qdrant en un solo paso.

        Si ``ids`` es ``None`` se generan UUIDs. Devuelve la lista de ids
        usados (útil para el ingest pipeline de Bulbapedia/Smogon).
        """
        if len(texts) != len(payloads):
            raise InfrastructureError(
                "texts y payloads deben tener la misma longitud",
                details={"texts": len(texts), "payloads": len(payloads)},
            )
        emb = embedder or get_embedder()
        vectors = emb.embed_batch(texts)
        if vectors and len(vectors[0]) != self.embedding_dim:
            raise InfrastructureError(
                "Dimensión del embedding no coincide con la colección",
                details={"got": len(vectors[0]), "expected": self.embedding_dim},
            )
        final_ids = ids or [uuid4().hex for _ in texts]
        self.upsert(
            collection=collection,
            ids=final_ids,
            vectors=vectors,
            payloads=payloads,
        )
        return final_ids

    def search_text(
        self,
        *,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        embedder: _Embedder | None = None,
    ) -> list[SearchHit]:
        """Búsqueda por texto: embebe la query y delega en ``search``."""
        emb = embedder or get_embedder()
        return self.search(
            collection=collection,
            query_vector=emb.embed(query),
            top_k=top_k,
            filters=filters,
        )

    def hybrid_search(
        self,
        *,
        collection: str,
        query: str,
        top_k: int = 5,
        must_filters: dict[str, Any] | None = None,
        embedder: _Embedder | None = None,
    ) -> list[SearchHit]:
        """Mismo flujo que ``search_text`` con énfasis semántico de "filtro obligatorio".

        Para hackathon Día 1 lo dejamos como alias; Día 3 le añadiremos
        BM25 sobre payloads vía ``MatchText`` cuando tengamos el corpus real.
        """
        return self.search_text(
            collection=collection,
            query=query,
            top_k=top_k,
            filters=must_filters,
            embedder=embedder,
        )


__all__ = ["SearchHit", "VectorStore"]
