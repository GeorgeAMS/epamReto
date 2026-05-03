"""Smoke test del endpoint /health."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_runs_lifespan() -> None:
    from api.main import create_app

    with TestClient(create_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "services" in body
