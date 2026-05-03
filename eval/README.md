# Eval — RAGAS + correctness

Suite de evaluación para Pokédex Arcana: dataset con contexto RAG, métricas RAGAS 0.2.x y checks numéricos/E2E sobre el dominio.

## Dataset

- **`eval/dataset.json`**: 30 filas (`question`, `category`, `ground_truth`, `contexts[]`, `correctness` opcional).
- Registro de batallas canónicas: **`eval/_fixtures_registry.py`** (alinea con `packages/domain/tests/fixtures.py`).

### Bloque `correctness`

| `type` | Comportamiento |
| --- | --- |
| `damage_calculator` | Compara daño y rango con `DamageCalculator` + fixture (siempre offline). |
| `orchestrator` | `Orchestrator.handle` con `CalculatorRequest` embebido; comprueba subcadenas en la respuesta final. **Si el LLM está en modo offline** (`ANTHROPIC_API_KEY` vacío), el sintetizador no mezcla la salida del calculator: esas filas **se omiten** con aviso. |

## Comandos

```powershell
# Dependencias eval (incluye ragas, datasets, pandas)
uv sync --extra dev --extra eval

# Correctness (8 numéricos + hasta 5 E2E si hay API Anthropic)
uv run python eval/run_correctness.py

# Forzar fallo si quedan E2E sin ejecutar (requiere ANTHROPIC_API_KEY real)
uv run python eval/run_correctness.py --require-anthropic
```

RAGAS (requiere **`OPENAI_API_KEY`** — LLM + embeddings por defecto):

```powershell
uv run python eval/run_ragas.py
```

- Sin clave: el script imprime un aviso y sale **0** (para no romper CI).
- `uv run python eval/run_ragas.py --require-openai`: sale **1** si falta la clave.
- Por defecto **`response` = `ground_truth`** (smoke del pipeline). Modo lento/real: `--live-orchestrator`.

Columnas esperadas por RAGAS 0.2: `user_input`, `response`, `retrieved_contexts`.

## Tests (schema)

```powershell
uv run pytest eval/test_dataset_schema.py -q
```

## Umbrales orientativos (manual)

| Métrica | Fuente | Objetivo guía |
| --- | --- | --- |
| faithfulness | RAGAS | ≥ 0.85 |
| answer_relevancy | RAGAS | ≥ 0.80 |
| llm_context_precision_without_reference | RAGAS | ≥ 0.75 |
| Numeric correctness | `run_correctness.py` | 100% en casos `damage_calculator` |
