"""Tipos compartidos entre capas (dominio ↔ agentes ↔ API).

Reglas:
- ``TraceId`` es un ``NewType`` sobre ``str`` para distinguirlo de un id arbitrario
  en la firma de funciones (sin coste en runtime).
- ``Confidence`` es un alias semántico de ``float`` en [0, 1]. La validación
  se hace en el value object/Pydantic field correspondiente.
- ``Source`` es la cita estructurada que llega del backend al frontend.
  Coincide en shape con ``domain.conversation.entities.Citation`` (que es
  pure-domain dataclass) — los agentes producen ``Source`` y el dominio los
  guarda como ``Citation`` en cada ``Turn``.
"""

from __future__ import annotations

from enum import Enum
from typing import NewType

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Trace id
# ---------------------------------------------------------------------------

TraceId = NewType("TraceId", str)
"""Identificador propagado a través de logs, Langfuse y cabeceras HTTP."""


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

Confidence = float
"""Confianza en [0, 1] de un agente sobre su respuesta.

Convenciones:
- ``1.0``  cálculo determinista (calculator_agent).
- ``0.95`` dato canon de PokéAPI/DuckDB.
- ``0.80`` RAG con ≥2 fuentes coincidentes.
- ``0.50`` respuesta parcial / cita única.
- ``0.0``  agente todavía no implementado / fallback.
"""


class ConfidenceLevel(str, Enum):
    """Tres categorías visibles para el usuario en la UI."""

    VERIFIED = "verified"
    PARTIAL = "partial"
    CONTRADICTION = "contradiction"


# Umbrales canon — afinables sin tocar callsites.
_VERIFIED_THRESHOLD = 0.80
_PARTIAL_THRESHOLD = 0.50


def confidence_to_level(value: Confidence) -> ConfidenceLevel:
    """Mapea un score continuo al enum de tres niveles para badges UI."""
    if value >= _VERIFIED_THRESHOLD:
        return ConfidenceLevel.VERIFIED
    if value >= _PARTIAL_THRESHOLD:
        return ConfidenceLevel.PARTIAL
    return ConfidenceLevel.CONTRADICTION


# ---------------------------------------------------------------------------
# Source / citation contract
# ---------------------------------------------------------------------------


class Source(BaseModel):
    """Cita estructurada que cualquier agente puede emitir.

    El frontend renderiza estas citas como chips ``[1]``, ``[2]`` con popover.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Id estable: pokeapi:garchomp, smogon:dragapult-ou, ...")
    title: str
    url: str | None = None
    snippet: str | None = Field(default=None, description="Trozo citable, ≤500 chars")
    kind: str = Field(
        default="unknown",
        description="pokeapi | smogon | bulbapedia | duckdb | computed | dataset",
    )


__all__ = [
    "Confidence",
    "ConfidenceLevel",
    "Source",
    "TraceId",
    "confidence_to_level",
]
