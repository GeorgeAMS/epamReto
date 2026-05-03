"""Tests del LLMClient. Modo offline (sin GROQ_API_KEY) — no toca red.

El test importante: ``stream`` y ``complete`` siguen funcionando con texto
determinístico para que la API arranque en demos sin créditos.
"""

from __future__ import annotations

from infrastructure.llm_client import (
    LLMClient,
    LLMOptions,
    LLMResponse,
    LLMRole,
)


def test_offline_complete_returns_deterministic_text() -> None:
    client = LLMClient(api_key="")
    a = client.complete("Hola", role=LLMRole.LIGHT)
    b = client.complete("Hola", role=LLMRole.LIGHT)
    assert isinstance(a, LLMResponse)
    assert a.text == b.text
    assert "[offline" in a.text
    assert a.model.endswith(":offline")


def test_offline_stream_yields_chunks() -> None:
    client = LLMClient(api_key="")
    chunks = list(client.stream("test", role=LLMRole.BRAIN, options=LLMOptions(max_tokens=64)))
    text = "".join(chunks)
    assert "[offline" in text
    assert len(chunks) >= 10  # tokenizado char-por-char


def test_role_selects_brain_or_light_model() -> None:
    client = LLMClient(api_key="", brain_model="brain-x", light_model="light-y")
    brain = client.complete("q", role=LLMRole.BRAIN)
    light = client.complete("q", role=LLMRole.LIGHT)
    assert brain.model.startswith("brain-x")
    assert light.model.startswith("light-y")


def test_complete_with_tools_offline_returns_no_tool_calls() -> None:
    client = LLMClient(api_key="")
    result = client.complete_with_tools("q", tools=[{"name": "search"}])
    assert result.tool_calls == []
    assert "[offline" in result.text


def test_is_offline_flag() -> None:
    online_like = LLMClient(api_key="sk-fake")
    offline = LLMClient(api_key="")
    assert offline.is_offline is True
    assert online_like.is_offline is False
