"""Errores tipados del monorepo.

Tres familias para que cualquier capa filtre la causa raíz sin string-matching:

- ``DomainError``         — invariantes del dominio (e.g., EVs > 510, move sin power).
- ``AgentError``          — fallos en la orquestación / formato de respuesta de un agente.
- ``InfrastructureError`` — fallos de red, BD, scrape, cache, observability.

``ValidationError`` es subclase de ``DomainError`` para que los value objects
puedan validar sus invariantes sin acoplarse a Pydantic en el dominio puro.
"""

from __future__ import annotations

from typing import Any


class ArcanaError(Exception):
    """Raíz común de todos los errores del proyecto.

    Mantenemos un atributo ``details`` (dict) para incluir contexto estructurado
    que la capa de logs/observability puede serializar a JSON sin extra magia.
    """

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def __repr__(self) -> str:  # pragma: no cover - cosmético
        return f"{self.__class__.__name__}({self.message!r}, details={self.details!r})"

    def to_dict(self) -> dict[str, Any]:
        """Serialización amigable para logs/respuesta API."""
        return {"type": self.__class__.__name__, "message": self.message, "details": self.details}


class DomainError(ArcanaError):
    """Error que surge dentro del núcleo de dominio (DDD).

    Usar cuando un invariante de modelo se rompe (e.g., calcular daño de un
    move STATUS, EVs negativos, equipo con duplicados, etc.).
    """


class ValidationError(DomainError):
    """Subclase específica para invariantes de value objects.

    Distinguirla de ``DomainError`` permite mapearla a HTTP 422 en la API y
    dejar ``DomainError`` "puro" para fallos de regla de negocio (HTTP 409).
    """


class AgentError(ArcanaError):
    """Error en la capa de agentes (LangGraph/multi-agent)."""


class InfrastructureError(ArcanaError):
    """Error en adaptadores externos (PokéAPI, Qdrant, Anthropic, OpenAI, etc.)."""


__all__ = [
    "AgentError",
    "ArcanaError",
    "DomainError",
    "InfrastructureError",
    "ValidationError",
]
