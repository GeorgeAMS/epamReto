# Pokédex Arcana

> Sistema multi-agente que responde preguntas complejas sobre Pokémon con
> **datos verificables**: stats, fórmula de daño Gen IX (determinística),
> estrategia competitiva, lore y memoria conversacional.

Hackathon-grade: demo funcional > perfección, con base limpia DDD pragmática.

---

## TL;DR

```bash
# 1) Bootstrap del entorno (uv recomendado)
uv sync                      # backend + workspace de packages
cd apps/web && npm install   # frontend

# 2) Servicios externos (Qdrant + Langfuse)
docker compose up -d

# 3) Variables de entorno
cp .env.example .env         # rellena GROQ_API_KEY, GEMINI_API_KEY

# 4) Dev loops
uv run uvicorn api.main:app --reload --port 8000   # API → :8000
cd apps/web && npm run dev                         # Web → :3000
```

Open <http://localhost:3000> y pregunta:
> *"If a Bold Abomasnow uses Blizzard against a Jigglypuff with 0 SpD EVs,
> how much damage does it do?"*

---

## Arquitectura (alto nivel)

```text
┌────────────┐   SSE   ┌──────────────┐   LangGraph   ┌──────────────────┐
│ Next.js 14 │ ──────► │ FastAPI :8000│ ────────────► │ Multi-agent flow │
└────────────┘         └──────────────┘               └────────┬─────────┘
                                                                │
                ┌───────────────────────────────────────────────┼─────────────┐
                │                                               │             │
        ┌───────▼────────┐  ┌───────────────┐  ┌────────────────▼──────┐  ┌──▼─────────┐
        │ stats_agent    │  │ calculator    │  │ strategy / lore (RAG) │  │ verifier   │
        │ (PokéAPI/DuckDB)│  │ (función pura)│  │ Qdrant + Sonnet 4.6   │  │ Sonnet 4.6 │
        └────────────────┘  └───────────────┘  └───────────────────────┘  └────────────┘
                                                       │
                                                       ▼
                                               ┌───────────────┐
                                               │ Synthesizer   │
                                               │ + citas [n]   │
                                               └───────────────┘
```

- **Orchestrator** (Haiku 4.5): clasifica intent + extrae entidades.
- **Calculator**: función Python pura, NUNCA un LLM (criterio de correctness).
- **Verifier**: re-ejecuta cálculos numéricos y devuelve `VERIFIED | PARTIAL | CONTRADICTION`.
- **Synthesizer** (Sonnet 4.6): respuesta final con citas inline `[1][2]`.

Detalle en [`ROADMAP.md`](./ROADMAP.md).

---

## Stack fijo

| Capa            | Tecnología |
|-----------------|------------|
| Backend         | Python 3.11, FastAPI, Pydantic v2, structlog |
| Agentes         | LangGraph 0.2 |
| LLM principal   | Groq **Llama 3.3 70B** (`llama-3.3-70b-versatile`) |
| LLM ligero      | Groq **Llama 3.1 8B** (`llama-3.1-8b-instant`) |
| Embeddings      | OpenAI `text-embedding-3-small` |
| Vector DB       | Qdrant (Docker) |
| Tabular         | DuckDB sobre CSVs Kaggle |
| Frontend        | Next.js 14 App Router + Tailwind + shadcn/ui + Framer Motion |
| Observability   | Langfuse self-hosted (Docker) |
| Eval            | RAGAS |

Versiones exactas en [`pyproject.toml`](./pyproject.toml) y
[`apps/web/package.json`](./apps/web/package.json).

---

## Estructura del repositorio

```text
pokedex-arcana/
├── apps/
│   ├── api/              # FastAPI (src/api/...)
│   └── web/              # Next.js 14
├── packages/
│   ├── domain/           # Núcleo DDD puro (src/domain/...)
│   ├── shared/           # Tipos + errores compartidos
│   ├── infrastructure/   # PokéAPI, Qdrant, DuckDB, Langfuse, LLM client
│   └── agents/           # LangGraph multi-agent
├── eval/                 # RAGAS + correctness numérico
├── data/                 # raw CSV/JSON → DuckDB
├── docker-compose.yml    # Qdrant + Langfuse + Postgres
├── pyproject.toml        # workspace uv (raíz)
└── ROADMAP.md            # checklist de fases
```

Cada paquete usa **src layout** y publica un wheel propio (gestionado por
uv workspaces).

---

## Reglas duras del proyecto

1. `domain/` no importa `requests`, `groq`, `fastapi`, ni nada de infra.
2. `calculator_agent` es función Python pura (jamás LLM).
3. Cada agente devuelve `AgentResponse(content, sources, confidence, trace_id)`.
4. Streaming **real** desde Anthropic API, nunca simulado.
5. Type hints obligatorios + Pydantic v2 entre capas.
6. Código en inglés, docstrings/comentarios en español.
7. Errores tipados: `DomainError`, `AgentError`, `InfrastructureError`.
8. Secrets sólo en `.env` (`.env.example` en repo).
9. Lenguaje ubicuo: `Nature`, `EV`, `IV`, `STAB`, `Tier` (no inventar nombres).

---

## Demo queries (ensayadas en `DEMO_SCRIPT.md`, FASE 7)

1. **Datos básicos**
   > *"What are Jigglypuff's types and base stats?"*
2. **Cálculo verificado**
   > *"If my Bold natured Abomasnow uses Blizzard against a Jigglypuff with
   > 0 SpD EVs, how much damage would it do?"*
3. **Team building con memoria**
   > *"Build me a competitive OU team that covers Dragapult's weaknesses."*
   > Follow-up: *"And against Gengar?"*

---

## Comandos útiles

```bash
# Backend
uv run pytest                                      # tests dominio + agentes
uv run ruff check .                                # lint
uv run mypy packages/domain                        # tipos del dominio
uv run uvicorn api.main:app --reload --port 8000   # API local

# Frontend
cd apps/web
npm run dev                                        # Next.js
npm run typecheck

# Servicios
docker compose up -d
docker compose logs -f langfuse                    # → http://localhost:3001
```

---

## Estado actual

**FASE 0 — Bootstrap completada.** Estructura del monorepo, workspace uv,
docker-compose con Qdrant + Langfuse, y `package.json` inicial del frontend
listos. Las siguientes fases se ejecutan secuencialmente — ver
[`ROADMAP.md`](./ROADMAP.md).
