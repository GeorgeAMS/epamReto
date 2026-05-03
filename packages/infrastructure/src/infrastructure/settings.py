"""Configuración global leída de variables de entorno.

Se inicializa una sola vez con `get_settings()` (cached). El dominio NO
debería importar este módulo — solo capa de aplicación e infraestructura.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings tipados con valores por defecto razonables para dev."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLMs ---
    groq_api_key: str = Field(default="")
    llm_brain_model: str = "llama-3.3-70b-versatile"
    llm_light_model: str = "llama-3.1-8b-instant"
    gemini_api_key: str = Field(default="")
    embedding_provider: str = "gemini"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "text-embedding-004"
    embedding_dim: int = 1536

    # --- Vector store ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection_lore: str = "pokedex_lore"
    qdrant_collection_strategy: str = "pokedex_strategy"

    # --- Datos estructurados ---
    duckdb_path: str = "./data/pokedex.duckdb"
    pokeapi_base_url: str = "https://pokeapi.co/api/v2"
    pokeapi_cache_path: str = "./data/cache/pokeapi.sqlite"

    # --- Observabilidad ---
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # --- API ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_log_level: str = "INFO"
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    reports_dir: str = "./reports"

    # --- Misc ---
    env: str = "dev"
    random_seed: int = 42

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    def ensure_data_dirs(self) -> None:
        """Crea las carpetas locales de datos si no existen."""
        for p in (self.duckdb_path, self.pokeapi_cache_path):
            Path(p).parent.mkdir(parents=True, exist_ok=True)
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]


def _bootstrap_dotenv() -> None:
    """Carga .env si no se cargó aún (para CLIs sueltos)."""
    if os.environ.get("_ARCANA_DOTENV_LOADED") == "1":
        return
    try:
        from dotenv import load_dotenv

        load_dotenv()
        os.environ["_ARCANA_DOTENV_LOADED"] = "1"
    except ImportError:
        pass


_bootstrap_dotenv()
