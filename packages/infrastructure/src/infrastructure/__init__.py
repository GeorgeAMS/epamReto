"""Capa de infraestructura de Pokédex Arcana.

Adaptadores que tocan el mundo exterior: PokéAPI, Qdrant, DuckDB, Langfuse,
Anthropic/OpenAI. Cualquier I/O bloqueante o de red vive aquí. El dominio
NUNCA importa este paquete.
"""

__version__ = "0.1.0"
