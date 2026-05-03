"""Tests del decorator @traced y del fallback NullLangfuse."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from infrastructure.observability import _NullLangfuse, traced


def test_get_langfuse_falls_back_to_null_when_no_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reseteamos el singleton interno + asegura settings sin credenciales.
    import infrastructure.observability as obs

    monkeypatch.setattr(obs, "_lf", None)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    # invalida cache de settings
    from infrastructure.settings import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    lf = obs.get_langfuse()
    assert isinstance(lf, _NullLangfuse)


@dataclass
class _FakeInput:
    trace_id: str = "trace-123"


def test_traced_passes_through_result_and_logs() -> None:
    @traced("dummy_agent")
    def run(self_obj: object, agent_input: _FakeInput) -> str:
        return f"hello {agent_input.trace_id}"

    out = run(object(), _FakeInput())
    assert out == "hello trace-123"


def test_traced_propagates_exceptions() -> None:
    @traced("explosive_agent")
    def boom(self_obj: object, agent_input: _FakeInput) -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        boom(object(), _FakeInput())


def test_traced_works_with_pydantic_like_result() -> None:
    class _Result:
        def model_dump(self) -> dict[str, str]:
            return {"agent": "dummy", "content": "ok"}

    @traced("dummy_agent")
    def run(self_obj: object, agent_input: _FakeInput) -> _Result:
        return _Result()

    out = run(object(), _FakeInput())
    assert isinstance(out, _Result)
