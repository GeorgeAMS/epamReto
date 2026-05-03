"""Tests del embedder Ollama con fallback determinístico.

Sin endpoint de Ollama, los vectores son hash-based pero **estables** y
**normalizados** — lo que ya basta para que Qdrant haga búsqueda coseno.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from infrastructure.embeddings import OllamaEmbedder
from shared.errors import InfrastructureError


@pytest.fixture
def embedder(tmp_path: Path) -> OllamaEmbedder:
    return OllamaEmbedder(base_url="http://127.0.0.1:9", dim=8, cache_path=str(tmp_path / "cache.sqlite"))


def test_offline_embedding_is_deterministic(embedder: OllamaEmbedder) -> None:
    a = embedder.embed("Pikachu")
    b = embedder.embed("Pikachu")
    assert a == b


def test_offline_embedding_is_normalized(embedder: OllamaEmbedder) -> None:
    v = embedder.embed("Garchomp es un pseudo-legendario Dragon/Ground")
    norm = math.sqrt(sum(x * x for x in v))
    assert math.isclose(norm, 1.0, rel_tol=1e-6)


def test_offline_embedding_dim_matches(embedder: OllamaEmbedder) -> None:
    assert len(embedder.embed("hola")) == 8


def test_distinct_inputs_produce_different_vectors(embedder: OllamaEmbedder) -> None:
    a = embedder.embed("fire")
    b = embedder.embed("water")
    # Los vectores no son idénticos
    assert any(abs(a[i] - b[i]) > 1e-9 for i in range(len(a)))


def test_embed_batch_uses_cache(embedder: OllamaEmbedder) -> None:
    first = embedder.embed_batch(["a", "b", "a", "c"])
    assert len(first) == 4
    assert first[0] == first[2]  # mismo texto → mismo vector


def test_empty_text_raises(embedder: OllamaEmbedder) -> None:
    with pytest.raises(InfrastructureError):
        embedder.embed("   ")


def test_is_offline_flag() -> None:
    embedder = OllamaEmbedder(base_url="http://127.0.0.1:9", dim=4)
    assert embedder.is_offline is False
