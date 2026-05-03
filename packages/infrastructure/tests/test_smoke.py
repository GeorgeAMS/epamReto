"""Smoke tests de infrastructure (sin red)."""

from __future__ import annotations

from infrastructure.settings import Settings


def test_settings_default_values() -> None:
    """Los defaults deben ser sensatos para dev local."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.env in ("dev", "prod")
    assert s.embedding_dim == 1536
    assert s.qdrant_url.startswith("http")


def test_cors_origins_list_parses_csv() -> None:
    s = Settings(_env_file=None, api_cors_origins="http://a.local, http://b.local")  # type: ignore[call-arg]
    assert s.cors_origins_list == ["http://a.local", "http://b.local"]
