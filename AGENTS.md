# AGENTS.md

## What this repo is

Sentinel = Behavioral Fraud Intelligence platform (fraud detection via behavioral anomaly detection, with optional Quantum ML). **Pre-implementation stage**: there is almost no production code yet. The authoritative content lives in `docs/` — read before implementing anything:

- `docs/RULES.md` — 69 engineering/research rules (the most important file)
- `docs/ARCHITECTURE.md`, `docs/SCHEMA.md`, `docs/TECH_STACK.md`, `docs/WORKFLOW.md`

Docs are written in Vietnamese; keep new docs/comments consistent with that convention.

## Environment & commands

- Python **3.12.11** pinned (`.python-version`), dependencies managed with **uv** (`uv.lock`).
- `uv sync` to install; run tools via `uv run <cmd>`.
- Lint/format: `uv run ruff check` / `uv run ruff format` (ruff is a dev dep; no `[tool.ruff]` config section exists).
- Tests: `uv run pytest`; single test: `uv run pytest tests/path::test_name`.
- The root `Makefile` is empty and `.github/workflows` has no CI — do not assume make targets or CI checks exist.

## Layout

```text
src/sentinel/{api,domain,features,models,services,data,config,utils}  # core package
scripts/{prepare_data,train,evaluate}.py                              # ML pipeline entrypoints
ui/                                                                   # Taipy presentation layer (app.py currently empty)
tests/{unit,integration}/                                             # currently empty scaffolding
configs/{dev,local,prod}.yaml                                         # environment configs
```

Planned stack: FastAPI (API boundary) + Taipy + Plotly (UI) + scikit-learn/XGBoost/LightGBM (classical) + Qiskit/qiskit-aer (quantum).

## Non-negotiable rules (from docs/RULES.md)

- **Classical first**: never build a quantum component without a hypothesis and a fair classical baseline benchmark (RULE-01..04).
- **Layer boundaries**: Taipy UI → API client → FastAPI → application services → domain/models. Routes stay thin (validate → call service → return); no business logic, feature engineering, or model inference in routes or UI (RULE-11..13).
- **UI must not invent data**: no fabricated scores, confidence values, or explanations not produced by the backend (RULE-09, RULE-45).
- **Classical independence**: the system must work if the quantum backend is unavailable (RULE-14).
- **No premature infrastructure**: modular monolith; no microservices/Kafka/K8s without measurable need (RULE-16..17).
- **Data discipline**: raw ≠ processed ≠ features ≠ model output ≠ decision; explicit contracts at boundaries; never call a raw score "confidence" (RULE-18..21).
- **No leakage**: respect temporal ordering in splits (train < validation < test); features must not use future information (RULE-27..28).
- **Metrics**: with imbalanced fraud data, never report Accuracy alone — use PR-AUC/F1/precision/recall (RULE-26).
- **Research ≠ production**: notebooks are experimental; promote only after validation; don't import notebook code into runtime (RULE-35..36).
- **Docs must match implementation**: update the relevant doc in `docs/` when changing architecture/schema/API behavior; each fact has one source-of-truth document (RULE-59..60).
- **No secrets/sensitive data committed**; credentials via env only (RULE-23, RULE-57).
