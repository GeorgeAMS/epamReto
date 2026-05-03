"""Contrato base de los agentes.

Todos los agentes (LLM o función pura) implementan ``BaseAgent.run`` y
devuelven ``AgentResponse`` — esto permite que el verifier procese la
salida de manera uniforme.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from shared.types import Confidence, ConfidenceLevel, Source, TraceId, confidence_to_level


class AgentInput(BaseModel):
    """Input estándar consumido por cualquier agente."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(description="Pregunta del usuario o sub-pregunta del orquestador")
    trace_id: TraceId = Field(default_factory=lambda: TraceId(uuid4().hex[:12]))
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Contexto resuelto: pokémon activos, conversation id, etc.",
    )


class AgentResponse(BaseModel):
    """Respuesta uniforme de cualquier agente.

    Campos clave que consume el verifier_agent:
    - ``confidence``: score [0,1].
    - ``sources``: lista de citas (puede ir vacía si es cálculo puro).
    - ``data``: payload tipado (el reporter lo serializa para PDF/MD).
    """

    model_config = ConfigDict(extra="forbid")

    agent: str = Field(description="Nombre del agente que produjo esta respuesta")
    content: str = Field(description="Texto markdown listo para mostrar al usuario")
    sources: list[Source] = Field(default_factory=list)
    confidence: Confidence = 0.5
    trace_id: TraceId
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Datos estructurados (cálculos, listas tabulares, etc.)",
    )

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return confidence_to_level(self.confidence)


class BaseAgent(ABC):
    """Clase base abstracta. Una subclase = un nodo del grafo LangGraph."""

    name: str

    def __init__(self, *, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__

    @abstractmethod
    def run(self, agent_input: AgentInput) -> AgentResponse:
        """Ejecuta el agente y devuelve respuesta uniforme."""

    async def arun(self, agent_input: AgentInput) -> AgentResponse:
        """Versión async por defecto: delega al sync. Subclases LLM la sobreescriben."""
        return self.run(agent_input)


__all__ = ["AgentInput", "AgentResponse", "BaseAgent"]
