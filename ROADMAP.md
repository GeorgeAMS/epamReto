# ROADMAP — Pokédex Arcana

Plan de ejecución por fases. Cada fase termina con criterio verificable.

---

## ✅ FASE 0 — Bootstrap

- [x] Estructura de carpetas: `apps/{api,web}`, `packages/{shared,domain,infrastructure,agents}`, `eval/`, `data/raw/`.
- [x] `README.md` y `ROADMAP.md`.
- [x] `.env.example` con TODAS las variables (Anthropic, OpenAI, Qdrant, Langfuse).
- [x] `.gitignore` para Python + Node.
- [x] `docker-compose.yml` con Qdrant + Langfuse + Postgres.
- [x] `pyproject.toml` raíz con workspace uv y per-package `pyproject.toml`.
- [x] `apps/web/package.json` inicial Next.js 14.

**Cómo verificar:**

```bash
docker compose config -q          # docker-compose válido
uv lock --check  || uv lock       # workspace resolves
ls packages/{shared,domain,agents,infrastructure}/pyproject.toml
```

---

## ⬜ FASE 1 — Dominio puro

- [ ] `packages/shared/src/shared/errors.py`: `DomainError`, `AgentError`, `InfrastructureError`, `ValidationError`.
- [ ] `packages/shared/src/shared/types.py`: `ConfidenceLevel`, `Confidence`, helpers.
- [ ] `packages/domain/src/domain/pokemon/value_objects.py`: `Type` (enum 18 tipos), `Stats`, `Nature` (25 naturalezas), `EV`, `IV`, `MoveCategory`, `Weather`, `Terrain`, `StatusCondition`, `BattleConditions`, `compute_effective_stat`.
- [ ] `packages/domain/src/domain/pokemon/entities.py`: `Pokemon`, `Move`, `Ability` (frozen dataclasses, `effective_stats()`, `stage_multiplier(...)`).
- [ ] `packages/domain/src/domain/pokemon/services.py`: ya existe — `TypeEffectiveness`, `DamageCalculator` (Gen IX completa: STAB, crit, weather, terrain, screens, burn, items básicos).
- [ ] `packages/domain/src/domain/team/{entities,services}.py`: ya existe — `Team`, `TeamMember`, `CoverageAnalyzer`, `SynergyScorer`.
- [ ] `packages/domain/src/domain/conversation/{entities,services}.py`: ya existe.
- [ ] `packages/domain/tests/test_damage_calculator.py`: **mínimo 10 casos** verificados Bulbapedia/Smogon.
- [ ] `pytest` verde end-to-end.

**Cómo verificar:**

```bash
uv run pytest packages/domain
uv run ruff check packages/domain packages/shared
```

---

## ⬜ FASE 2 — Infraestructura

- [ ] `infrastructure/llm_client.py`: wrapper Anthropic (`complete`, `stream`, `complete_with_tools`) con Sonnet/Haiku.
- [ ] `infrastructure/pokeapi_client.py`: cliente async aiohttp + cache aiosqlite.
- [ ] `infrastructure/duckdb_client.py`: queries sobre CSVs Kaggle.
- [ ] `infrastructure/vector_store.py`: wrapper Qdrant (`upsert`, `search`, `hybrid_search`).
- [ ] `infrastructure/observability.py`: cliente Langfuse + decorator `@traced(agent_name)`.
- [ ] `infrastructure/ingestion/pokeapi_ingest.py`: descarga 1025 Pokémon a SQLite.
- [ ] `infrastructure/ingestion/csv_ingest.py`: CSVs `data/raw/` → DuckDB.
- [ ] `infrastructure/ingestion/bulbapedia_ingest.py`: scrape + chunk + embed → Qdrant (no se ejecuta aún).

---

## ⬜ FASE 3 — Agentes (LangGraph)

- [ ] `agents/base.py`: `Agent` ABC + `AgentResponse(content, sources, confidence, trace_id)` Pydantic.
- [ ] `agents/orchestrator.py`: clasifica intent (Haiku) + arma grafo con routing condicional.
- [ ] `agents/stats_agent.py`: PokéAPI cache + DuckDB.
- [ ] `agents/calculator_agent.py`: PURO Python, llama a `domain.DamageCalculator`.
- [ ] `agents/lore_agent.py`: RAG sobre Qdrant `lore`.
- [ ] `agents/strategy_agent.py`: RAG sobre Qdrant `competitive` + Sonnet.
- [ ] `agents/verifier_agent.py`: cross-check números + claims, devuelve confidence.
- [ ] `agents/synthesizer.py`: respuesta final streaming Sonnet con citas inline.
- [ ] `agents/reporter_agent.py`: Markdown → PDF con weasyprint.

---

## ⬜ FASE 4 — API FastAPI

- [ ] `apps/api/src/api/main.py`: app + CORS + routers + middleware logs.
- [ ] `routers/chat.py`: `POST /chat` SSE streaming, `conversation_id`.
- [ ] `routers/conversations.py`: CRUD en memoria.
- [ ] `routers/reports.py`: `POST /reports/generate` → PDF.
- [ ] `routers/observability.py`: `GET /traces/{conversation_id}`.
- [ ] `dependencies.py`: inyección orchestrator/vector_store.
- [ ] `middleware.py`: structlog + propagación de `trace_id`.

---

## ⬜ FASE 5 — Frontend (Next.js 14)

- [ ] Setup Next.js + Tailwind + shadcn/ui + tema dark con `#FFD700` / `#3B4CCA`.
- [ ] `app/page.tsx`: layout grid 2 cols (chat + agent trace).
- [ ] `components/Chat.tsx`: streaming SSE, render markdown, citas clickeables.
- [ ] `components/AgentTracePanel.tsx`: timeline animada con Framer Motion.
- [ ] `components/DamageVisualizer.tsx`: barra HP animada.
- [ ] `components/TeamBuilder.tsx`: 6 sprites + heatmap de coberturas.
- [ ] `components/ConfidenceBadge.tsx`: ✅/⚠️/❌.
- [ ] `components/AgentGraphModal.tsx`: react-flow del grafo.
- [ ] `components/CitationPopover.tsx`: hover/click con snippet.
- [ ] `lib/api.ts`: fetch + EventSource.
- [ ] `lib/types.ts`: tipos TS espejo de Pydantic.
- [ ] Botón "Generate Report".

---

## ⬜ FASE 6 — Eval

- [ ] `eval/dataset.json`: 30 preguntas etiquetadas (categoría + respuesta esperada).
- [ ] `eval/run_ragas.py`: faithfulness + answer_relevancy + context_precision.
- [ ] `eval/run_correctness.py`: match exacto en preguntas numéricas.
- [ ] `eval/README.md`: guía de uso.

---

## ⬜ FASE 7 — Demo prep

- [ ] `DEMO_SCRIPT.md`: las 3 queries killer ensayadas.
- [ ] `Makefile`: `setup`, `dev-api`, `dev-web`, `ingest`, `eval`, `demo`.
- [ ] README final con diagrama ASCII + cómo demostrar.
