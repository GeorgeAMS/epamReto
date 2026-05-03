"""Cliente de embeddings Ollama con cache local + fallback determinístico.

Reglas:
- Modelo configurable vía ``settings.embedding_model``
  (default ``nomic-embed-text``, dim 768).
- Cache persistente con diskcache: la **misma string** siempre devuelve el
  mismo vector, evitando recomputo durante demos repetidas.
- Si Ollama no responde se cae a un embedding determinístico (hash
  → vector pseudoaleatorio normalizado). Permite que la pipeline RAG corra
  end-to-end sin la API durante desarrollo.

Diseñado pensando en que el `vector_store.upsert_documents` lo consume.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import diskcache
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Fallback determinístico
# ---------------------------------------------------------------------------


def _deterministic_embedding(text: str, dim: int) -> list[float]:
    """Vector pseudoaleatorio derivado del hash del texto.

    Propiedades útiles:
    - Estable: misma entrada → mismo vector.
    - Normalizado a norma L2 = 1 (para que las búsquedas con coseno funcionen).
    - Distribución suficientemente dispersa para que strings distintas no
      colapsen al mismo vector.
    """
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    # Generador lineal congruencial sencillo: rápido y reproducible.
    state = seed or 1
    raw: list[float] = []
    for _ in range(dim):
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        # Mapea a [-1, 1]
        raw.append(((state >> 33) / (2**31)) - 1.0)
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


class OllamaEmbedder:
    """Embedder compatible con endpoint `/api/embeddings` de Ollama."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        dim: int | None = None,
        cache_path: str | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.ollama_base_url
        self._model = model or settings.embedding_model
        self._dim = dim or settings.embedding_dim

        cache_dir = Path(cache_path or settings.pokeapi_cache_path).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(cache_dir / "embeddings-disk"))

        self._sdk: Any | None = None

    @property
    def is_offline(self) -> bool:
        # Modo online/offline se evalúa por request real; aquí mantenemos True
        # solo para compat con tests existentes cuando no hay endpoint.
        return False

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model(self) -> str:
        return self._model

    # --- helpers ---------------------------------------------------------

    def _cache_key(self, text: str) -> str:
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()
        return f"{self._model}:{self._dim}:{h}"

    # --- API pública -----------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """Embebe una sola string. Resultado cacheado en disco."""
        if not text or not text.strip():
            raise InfrastructureError(
                "Texto vacío no se puede embeber",
                details={"len": len(text)},
            )

        cached = self._cache.get(self._cache_key(text))
        if cached is not None:
            return list(cached)  # type: ignore[arg-type]

        try:
            vector = self._embed_remote([text])[0]
        except InfrastructureError:
            vector = _deterministic_embedding(text, self._dim)

        self._cache.set(self._cache_key(text), vector)
        return vector

    def embed_batch(self, texts: Iterable[str]) -> list[list[float]]:
        """Embebe en lote. Reutiliza cache; sólo manda a la API los miss."""
        items = list(texts)
        if not items:
            return []

        # Identifica cuáles están en cache.
        cached_results: list[list[float] | None] = []
        miss_indices: list[int] = []
        miss_texts: list[str] = []
        for idx, t in enumerate(items):
            if not t or not t.strip():
                raise InfrastructureError(
                    "Texto vacío no se puede embeber",
                    details={"index": idx},
                )
            hit = self._cache.get(self._cache_key(t))
            if hit is None:
                cached_results.append(None)
                miss_indices.append(idx)
                miss_texts.append(t)
            else:
                cached_results.append(list(hit))  # type: ignore[arg-type]

        if miss_texts:
            new_vectors: list[list[float]]
            try:
                new_vectors = self._embed_remote(miss_texts)
            except InfrastructureError:
                new_vectors = [_deterministic_embedding(t, self._dim) for t in miss_texts]
            for local_i, mi in enumerate(miss_indices):
                vec = new_vectors[local_i]
                cached_results[mi] = vec
                self._cache.set(self._cache_key(miss_texts[local_i]), vec)

        return [v for v in cached_results if v is not None]

    # --- Llamada remota (con retry) -------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=4),
        retry=retry_if_exception_type(InfrastructureError),
    )
    def _embed_remote(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for t in texts:
            try:
                response = requests.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": t},
                    timeout=60,
                )
                response.raise_for_status()
                vectors.append(list(response.json().get("embedding", [])))
            except Exception as exc:
                raise InfrastructureError(
                    "Ollama embeddings fallo",
                    details={"model": self._model, "error": str(exc)},
                ) from exc
        if any(len(v) != self._dim for v in vectors):
            log.warning(
                "embeddings.dim_mismatch",
                expected=self._dim,
                got=[len(v) for v in vectors[:1]],
            )
        return vectors


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_embedder: OllamaEmbedder | None = None


def get_embedder() -> OllamaEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = OllamaEmbedder()
        log.info(
            "embedder.ready",
            offline=_embedder.is_offline,
            model=_embedder.model,
            dim=_embedder.dim,
        )
    return _embedder


__all__ = ["OllamaEmbedder", "get_embedder"]
