"""Núcleo de dominio (DDD) de Pokédex Arcana.

Bounded contexts:
- ``domain.pokemon``        — entidades, value objects y servicios de combate.
- ``domain.team``           — team building y análisis de coberturas.
- ``domain.conversation``   — memoria conversacional y resolución de contexto.

Regla dura: este paquete no importa requests, anthropic, fastapi ni nada
de infraestructura. Es código puro auditable.
"""

__version__ = "0.1.0"
