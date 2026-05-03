"""Capa multi-agente (LangGraph) de Pokédex Arcana.

Agentes:
- ``orchestrator``     — clasifica intent + arma el grafo (Haiku 4.5).
- ``stats_agent``      — datos básicos (PokéAPI/DuckDB).
- ``calculator_agent`` — función pura: delega al dominio.
- ``lore_agent``       — RAG sobre Bulbapedia.
- ``strategy_agent``   — RAG sobre Smogon + razonamiento Sonnet 4.6.
- ``verifier_agent``   — cross-check de números y claims.
- ``synthesizer``      — respuesta final con citas inline.
- ``reporter_agent``   — Markdown + PDF.
"""

__version__ = "0.1.0"
