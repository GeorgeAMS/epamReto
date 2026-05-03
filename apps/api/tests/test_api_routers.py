"""Tests de routers con orchestrator/reporter fake (sin red externa)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from agents.base import AgentResponse
from agents.reporter_agent import ReporterAgent
from shared.types import Source, TraceId


class FakeOrchestrator:
    """Sustituye el grafo real: respuestas deterministas."""

    def handle(
        self,
        query: str,
        *,
        trace_id: TraceId | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            agent="synthesizer",
            content=f"Synth: {query}",
            sources=[
                Source(
                    id="t1",
                    title="Test",
                    url="https://example.com",
                    kind="dataset",
                ),
            ],
            confidence=0.92,
            trace_id=TraceId(str(trace_id or "trace-fake")),
            data={"context_keys": sorted((context or {}).keys())},
        )

    def handle_stream(
        self,
        query: str,
        *,
        trace_id: TraceId | None = None,
        context: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        tid = str(trace_id or "st")
        yield {
            "event": "intent",
            "data": json.dumps({"intent": "stats", "entities": {}}),
        }
        yield {
            "event": "agent",
            "data": json.dumps(
                {"agent": "stats_agent", "confidence": 0.9, "sources": []},
            ),
        }
        yield {"event": "token", "data": "He"}
        yield {"event": "token", "data": "llo"}
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "trace_id": tid,
                    "confidence": 0.9,
                    "confidence_level": "verified",
                    "sources": [],
                    "data": {},
                },
            ),
        }


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    from api.dependencies import get_orchestrator, get_reporter
    from api.main import create_app

    app = create_app()

    def _orch() -> FakeOrchestrator:
        return FakeOrchestrator()

    def _rep() -> ReporterAgent:
        return ReporterAgent(output_dir=tmp_path / "reports")

    app.dependency_overrides[get_orchestrator] = _orch
    app.dependency_overrides[get_reporter] = _rep
    with TestClient(app) as test_client:
        yield test_client


def test_post_chat_returns_chat_response(client: TestClient) -> None:
    r = client.post("/chat", json={"query": "What types does Pikachu have?"})
    assert r.status_code == 200
    body = r.json()
    assert body["agent"] == "synthesizer"
    assert body["confidence"] == pytest.approx(0.92)
    assert body["conversation_id"]
    assert body["trace_id"]


def test_post_chat_passes_context(client: TestClient) -> None:
    r = client.post(
        "/chat",
        json={"query": "damage calc", "context": {"calculator_request": {"mock": 1}}},
    )
    assert r.status_code == 200
    assert r.json()["data"]["context_keys"] == ["calculator_request"]


def test_conversations_turns_and_trace(client: TestClient) -> None:
    r0 = client.post("/chat", json={"query": "hi"})
    cid = r0.json()["conversation_id"]

    tr = client.get(f"/traces/{cid}")
    assert tr.status_code == 200
    body = tr.json()
    assert "timeline" in body
    assert any(e["kind"] == "chat_sync" for e in body["timeline"])

    turns = client.get(f"/conversations/{cid}/turns")
    assert turns.status_code == 200
    assert len(turns.json()) == 2


def test_chat_stream_contains_events(client: TestClient) -> None:
    conv = client.post("/conversations")
    assert conv.status_code == 201
    cid = conv.json()["id"]

    with client.stream(
        "POST",
        "/chat/stream",
        json={"query": "hello stream", "conversation_id": cid},
    ) as resp:
        assert resp.status_code == 200
        payload = b"".join(resp.iter_bytes())

    assert b"event: intent" in payload
    assert b"event: agent" in payload
    # Cada token es su propia línea `data:` — no hay una subcadena "Hello" contigua.
    assert b"data: He" in payload or b"data: He\r" in payload
    assert b"event: done" in payload or b'"confidence_level"' in payload


def test_report_generate_writes_markdown(client: TestClient) -> None:
    r = client.post(
        "/reports/generate",
        json={"query": "Report me Garchomp"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["md_path"]
    assert Path(body["md_path"]).exists()
