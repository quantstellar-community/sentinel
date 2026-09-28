# Sentinel

**Behavioral Fraud Intelligence**

Sentinel is a behavioral fraud intelligence platform. Instead of classifying transactions as fraudulent or not in isolation, Sentinel learns what normal behavior looks like, measures meaningful deviations, and translates them into explainable anomaly and risk signals.

> **Status:** Early research & pre-implementation foundation. Production pipelines, public API, and deployed quantum circuits are not yet considered complete.

---

## Overview

Traditional fraud detection models a transaction as a single classification event:

```text
Transaction → Fraud / Non-Fraud
```

Sentinel instead reasons about behavior:

```text
Transaction History → Behavioral Context → Behavioral Representation
        → Expected / Normal Behavior → Deviation → Anomaly → Risk → Decision Support
```

The core principle is:

> **Learn normal behavior first; detect meaningful deviations second.**

An anomaly is not assumed to be fraud. Sentinel therefore keeps **anomaly detection**, **risk assessment**, and **final decision** as distinct concerns, and always acts as decision support rather than an autonomous decision maker.

The first use case is **card-not-present and digital-payment fraud** — a domain with severe class imbalance, temporally evolving fraud patterns, and a strong need for explainability.

### Design principles

- **Classical first** — every quantum approach requires a scientific hypothesis and a fair classical baseline. Quantum is used *where justified*, never by default.
- **Fair benchmark** — quantum and classical methods are compared under a consistent, reproducible evaluation protocol.
- **Evidence over hype** — results are reported together with limitations, computational cost, noise, and practical utility.
- **Anomaly ≠ fraud** — anomalies are signals to be investigated, not verdicts.
- **No premature infrastructure** — a modular monolith; infrastructure is added only when workload or product requirements demand it.

---

## Architecture

Sentinel is an **API-first modular monolith** organized as a behavioral intelligence pipeline:

```text
Event / Transaction Data
        ↓
Data & Context Layer
        ↓
Behavioral Representation
        ↓
Normal / Expected Behavior
        ↓
Deviation Analysis
        ↓
Anomaly Intelligence
        ↓
Risk / Decision Support
```

Quantum is positioned strictly as a **research enhancement layer**, benchmarked against a classical counterpart:

```text
Behavioral Representation
        ↓
Classical Baseline
        ↓
Quantum Representation / Similarity
        ↓
Fair Benchmark
        ↓
Validated Intelligence
```

The classical baseline core consists of Logistic Regression, LightGBM, and a classical One-Class SVM. The V1 quantum research direction prioritizes **quantum kernels with OCSVM**.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture.

---

## Evaluation

Because fraud data is severely imbalanced, accuracy is never used as the primary criterion. Evaluation focuses on:

- PR-AUC / AUPRC, ROC-AUC
- Precision / Recall, F1
- False-positive / false-negative analysis
- Calibration, robustness, and temporal generalization
- Inference latency and resource requirements
- Explainability

Splits respect temporal ordering, and every quantum experiment records its full execution context (dataset, split, feature representation, model config, qubits, circuit depth, shots, noise, runtime). See [docs/RULES.md](docs/RULES.md).

---

## Getting Started

Requires **Python 3.12** and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check
uv run ruff format
```

### Data & ML pipeline

```bash
# Fetch the European credit-card dataset (requires Kaggle credentials)
uv run python scripts/fetch_data.py

# Prepare and split data
uv run python scripts/prepare_data.py

# Train classical baseline
uv run python scripts/train.py

# Evaluate models
uv run python scripts/evaluate.py
```

The research dataset is an anonymized European credit-card fraud set: 284,807 transactions, 492 fraud cases (~0.17% fraud rate), 28 PCA-transformed features, transaction time and amount. It is sufficient for classical baselines, one-class learning, and quantum-kernel experiments, but lacks the rich entity/temporal context required to validate the full behavioral-trajectory vision.

---

## Project Structure

```text
src/sentinel/              # Core package
  ├── api/                 # FastAPI routes & schemas
  ├── data/                # Ingestion, preprocessing, validation
  ├── domain/              # Core business concepts
  ├── features/            # Behavioral & temporal features
  ├── models/              # Classical and quantum models
  ├── services/            # Application orchestration
  ├── config/              # Settings
  └── utils/

scripts/                   # ML pipeline entrypoints (data → train → evaluate)
research/                  # Experimental notebooks & references (not production)
configs/                   # Environment configuration
docs/                      # Project documentation
tests/                     # Unit and integration tests
```

---

## Documentation

| Document | Purpose |
|---|---|
| [PRD.md](docs/PRD.md) | Product requirements |
| [DESIGN.md](docs/DESIGN.md) | Product / UI design |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [SCHEMA.md](docs/SCHEMA.md) | Data and interface contracts |
| [RULES.md](docs/RULES.md) | Engineering & research rules |
| [TECH_STACK.md](docs/TECH_STACK.md) | Technology stack |
| [WORKFLOW.md](docs/WORKFLOW.md) | Research & development workflow |
| [ADR/](docs/ADR/) | Architecture decision records |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |

---

## Roadmap

```text
Phase 0 — Research Contract        → data schema, problem formulation, evaluation protocol
Phase 1 — Classical Baseline       → reproducible pipeline, behavioral features, anomaly detection
Phase 2 — Hybrid / Quantum Layer   → quantum kernels, OCSVM, fair classical-vs-quantum benchmarking
Phase 3 — Behavioral State Intel.  → temporal state, entity context, expected-vs-observed deviation
Phase 4 — Sentinel Platform        → reusable behavioral intelligence service, investigation UI
```

---

## License

Copyright © 2026 Quantstellar Technologies.

This project is proprietary software. All rights reserved. See [LICENSE](./LICENSE).