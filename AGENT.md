# AGENT.md — Sentinel

Operating guide for whoever takes this over, human or agent. Describes the
**architecture as built**, the **results measured**, and **how to run it**.

> Three other documents, read as needed: [`PIPELINE_V2.md`](PIPELINE_V2.md) is the
> detailed per-layer architecture design; [`history.md`](history.md),
> [`diary_v2.md`](diary_v2.md) and [`diary_v3.md`](diary_v3.md) are build logs in
> chronological order, recording rejected decisions and why they were rejected.

---

## 1. What this project is

A behavioural anomaly intelligence platform, first applied to payment fraud. The
governing principle: **learn the normal world first, detect deviations from it
second** — keeping anomaly detection separate from the final fraud decision.

Two datasets, and the architecture is built so that **adding a third requires no
change to layers 5–10**:

| | creditcard | IEEE-CIS |
|---|---:|---:|
| Transactions | 284,807 | 590,540 |
| Fraud | 492 (0.17%) | 20,663 (3.50%) |
| Time span | 2 days | 182 days |
| Columns (after join) | 31 | 434 |
| Carries entity information | ❌ | ✅ (`card1+card2+addr1`) |
| CV folds | 4 | 6 |

---

## 2. Four invariants — violating one is a bug, not a trade-off

Every layer boundary exists to protect at least one of these. Check them before
changing anything.

**I. Information flows only from past to future.** No number used for training or
transformation may originate from data beyond the evaluation boundary. This
includes **every aggregate statistic in the feature layer** — the easiest place
to violate it and the hardest to detect.

**II. How much label information a model sees is an explicit declaration.** Every
model passes through a `LabelRegime` gate declaring track A, B, or C. True labels
are **always** used at evaluation, regardless of what the model saw during
training.

**III. Differences between datasets are isolated in the first two layers.** From
layer 4 down, no layer knows which dataset is running. **Never write
`if spec.name == "..."` below layer 1** — wanting to branch means the spec is
missing a declaration.

**IV. Every comparison is paired on identical rows, and raw scores must outlive
the run that produced them.** Recomputing later is not equivalent: it drags in
every library-version and seed difference that pairing exists to cancel.

> **How to read results:** a leaderboard sorted by mean AUPRC is **not a
> conclusion**. Conclusions come from `compare_models.py` (paired bootstrap,
> 2,000 draws).

---

## 3. Project structure

### Ten layers, mapped to source

| Layer | Responsibility | File | Lines |
|---|---|---|---:|
| 1 | Domain Adapter — datasets declared as data, not code | `src/datasets/spec.py` · `creditcard.py` · `ieeecis.py` | 347 |
| 2 | Ingestion — load · join · validate · dedup · sort | `src/data/loader.py` | 262 |
| 3 | Temporal Partition — expanding **and sliding** windows | `src/data/splitter.py` | 292 |
| 4 | Feature Pipeline — composable, self-declaring groups | `src/features/base.py` · `structural.py` · `behavioral.py` | 861 |
| 5 | Label Regime — the A/B/C label gate | `src/models/regime.py` | 172 |
| 6 | Model — features in, risk score out | `src/models/*.py` | 1,414 |
| 7 | Execution — orchestration · timing · persistence | `src/evaluation/runner.py` | 485 |
| 8 | Evaluation — AUPRC + CI · paired bootstrap | `src/evaluation/metrics.py` | 372 |
| 9 | Drift Protocol — decay over time | `src/evaluation/drift.py` | 383 |
| 10 | Explanation — TreeSHAP + counterfactual | `src/evaluation/explain.py` | 358 |

Totals: **5,593 lines `src/`** · **1,493 lines `scripts/`** · **3,756 lines
`tests/`** (366 tests).

### Directory tree

```text
sentinel/
├── src/
│   ├── config.py                 protocol constants: SEED, N_BOOTSTRAP, warning thresholds
│   ├── datasets/                 LAYER 1 — spec.py + one file per dataset
│   ├── data/                     LAYERS 2-3 — loader · splitter · preprocessor
│   ├── features/                 LAYER 4 — base · structural · behavioral
│   ├── models/                   LAYERS 5-6 — regime · base · supervised · anomaly
│   │                                          hybrid · behavioral · tuning · pu
│   └── evaluation/               LAYERS 7-10 — runner · metrics · drift · explain
├── scripts/                      command-line entry points (see §5)
├── tests/                        366 tests
├── datasets/                     (gitignored — raw data + materialised splits)
│   ├── creditcard.csv
│   ├── ieeecis-fraud-detection/
│   └── processed/<dataset>/      dev.parquet · holdout.parquet · split_manifest.json
├── experiments/results/          (gitignored — records + raw scores)
│   └── <dataset>/<model>/        record.json · scores.npz · decay.json · explanations.json
├── docs/                         evaluation protocol · research synthesis · project guide
├── notebooks/01_eda.ipynb
├── PIPELINE_V2.md                detailed architecture design
├── history.md · diary_v2.md · diary_v3.md    build logs
└── AGENT.md                      this file
```

### Model registry — 22 models, organised by label budget

The organising axis is **how much label information the model sees**, not the
algorithm. The same algorithm under two regimes is two different experiments.

| Track | What `fit` sees | Models |
|---|---|---|
| **A** — Supervised | X + full labels | `logreg` · `logreg_full_scale` · `xgboost` · `xgboost_unweighted` · **`xgboost_tuned`** · `lightgbm` · `lightgbm_unweighted` · **`lightgbm_tuned`** · `xgboost_hybrid` · `xgboost_hybrid_iforest` · `xgboost_behavioral`* · `xgboost_behavioral_only`* · `xgboost_hybrid_behavioral`* |
| **B** — One-class | X of the normal class only | `isolation_forest` · `isolation_forest_with_time` · `autoencoder` · `autoencoder_minimal_scale` · `isolation_forest_behavioral`* · `autoencoder_behavioral`* |
| **C** — Unlabeled | All of X, **no labels**, real fraud contamination intact | `if_contaminated` · `ae_contaminated` · `pu_cascade` |

`*` = requires entity information, so runs on IEEE-CIS only (15 models apply to
creditcard, 22 to IEEE-CIS).

**Registry discipline:** no model enters the registry without a measurable
question attached to it.

---

## 4. Measured results

### 4.1 IEEE-CIS leaderboard (AUPRC on validation folds)

| Model | Track | AUPRC | Note |
|---|:---:|---:|---|
| **`lightgbm_tuned`** | A | **0.6096** | Champion · ROC-AUC 0.9127 · **P@100 0.993** |
| `lightgbm_unweighted` | A | 0.5937 | |
| `xgboost_tuned` | A | 0.5861 | |
| `xgboost_unweighted` | A | 0.5790 | |
| `lightgbm` | A | 0.5662 | |
| `xgboost_hybrid_iforest` | A | 0.5408 | |
| `xgboost` | A | 0.5393 | Historical baseline; anchors every recorded comparison |
| `xgboost_hybrid` | A | 0.5389 | Anomaly layer: **null** |
| `xgboost_behavioral` | A | 0.5379 | Behavioural features: **null** |
| `xgboost_hybrid_behavioral` | A | 0.5371 | |
| `if_contaminated` | C | 0.1956 | |
| `logreg` | A | 0.1899 | |
| `isolation_forest` | B | 0.1877 | |
| `isolation_forest_behavioral` | B | 0.1737 | Behavioural features: **harmful** (lost 6/6) |
| `pu_cascade` | C | 0.1607 | Loses to its own `if_contaminated` baseline |
| `xgboost_behavioral_only` | A | 0.1089 | 26 behavioural columns alone, lift 4.5× |
| `ae_contaminated` | C | 0.0937 | |
| `autoencoder` | B | 0.0922 | |
| `autoencoder_behavioral` | B | 0.0888 | |
| `autoencoder_minimal_scale` | B | 0.0778 | |

On creditcard the champion is `xgboost` at **0.7741** (per-fold
`[0.8168, 0.6668, 0.8213, 0.7916]`). That number is the **migration
constraint** — see §6.

> **Never compare bare AUPRC across the two datasets** — the random floors differ
> (0.0015 vs 0.0365). Use `lift_over_random`.

### 4.2 Six principal findings

**1. Hyperparameter tuning is the most effective improvement found — but only
where the model has interacting hyperparameters to search.**
`lightgbm_tuned` gains +0.0159 over the best previously known configuration
(significant on 4/6 folds, worse on 0), `xgboost_tuned` +0.0071 (4/6, worse on
0). `logreg_tuned` does not: +0.0003 against `logreg_full_scale`, significantly
better on 2 folds and worse on 2 — noise, not an effect. Its 14-point space has
one parameter that carries signal (`class_weight`), and `logreg_full_scale`
already fixes it at the winning value; `C`, the only thing left to search, is
nearly flat across four orders of magnitude (0.1942–0.1977 inner AUPRC). A
linear model has no `max_depth` / `subsample` / `colsample_bytree` combinations
to exploit, so the earlier "tuning pays" finding does not generalise
unconditionally — it holds for tree ensembles, not for every model in the
registry.

**2. Behavioural features do not help on IEEE-CIS — and the mechanism is known.**
All four comparisons are negative; against Isolation Forest they lose **6/6
folds**. Mechanism: the 26 behavioural columns take only **4.70% of XGBoost's
gain** while being 5.68% of the columns, and the top-15 most important columns
include `C1`, `C4`, `C8`, `C12`, `C14` — **Vesta's own counting features, built
for exactly this purpose**. Not "useless" but **redundant**.

The obvious objection — that the composite entity proxy fragments customers and
starves the features — was tested directly and rejected. Under `card1` alone,
which reaches 97.7% usable history against the composite key's 91.9%, the gap
does not close: −0.0037 against the baseline, slightly *wider* than the
composite key's −0.0014. A better proxy does not rescue the features, which is
what turns "redundant" from a hypothesis into the surviving explanation. The
variant lives on as the `ieeecis_card1` spec so the comparison stays repeatable.

**3. The anomaly layer still contributes nothing**, on either dataset, even with
42× more fraud on IEEE-CIS. `xgboost_hybrid` 0.5389 vs `xgboost` 0.5393.

**4. Drift: recency matters far more than training-set volume — 82% vs 18%.**
Measured with three arms (frozen / sliding / expanding) and paired bootstrap;
recency is significant on **5/5 blocks**. The sharper finding: **the cost of
stale data grows with time distance** (+0.0221 at block 2 → +0.1071 at block 6)
while the benefit of accumulating history stays **flat** (~+0.017). Operational
consequence: *the less often you retrain, the more recency dominates*.

Repeated on the champion, `lightgbm_tuned`, the split holds (75% / 25%, again
significant on 5/5 and 4/5 blocks) — but it decays **almost twice as fast**:
−15.9% frozen over the period against `xgboost`'s −9.3%. The consequence is
worth stating plainly, because it makes the tuning gain conditional:

```
block 6, expanding : lightgbm_tuned 0.6359  vs  xgboost 0.5457   gap +0.0902
block 6, frozen    : lightgbm_tuned 0.4607  vs  xgboost 0.4258   gap +0.0349
```

**Freezing erodes 61% of the tuning advantage.** A tighter fit to the training
distribution is exactly what tuning buys, and exactly what a drifting
distribution takes back. Tune *and* retrain, or much of the gain is notional.

**5. Two blocks of history are as good as all of it.** Sweeping the sliding
window's width shows the curve saturating immediately: width 1 is significantly
*worse* than the expanding arm (−0.0128, interval excludes zero), but width 2
already matches it (+0.0016, interval covers zero) on **33% of the data**.
Widths 2–5 all land between 0.5397 and 0.5414, non-monotonically — the two that
test "significantly better" are noise, not a trend. Operationally: keep about
two blocks (~60 days); the remaining 67% of the history buys nothing measurable,
so training cost drops 3× for free.

**6. `pu_cascade` loses to the very detector it learns from**, on both datasets.
Structural reason: thresholding a continuous anomaly score into binary labels
**destroys the ordering information** inside each group. And
`assumed_positive_rate` — which drives most of the result — is precisely the
quantity you cannot measure while label-blind.

### 4.3 Four documented expectations that measurement refuted

Recorded so nobody repeats them: (1) B−C scales with contamination — exactly
backwards; (2) the entity-proxy table in diary_v2 — wrong, caused by the
`entity_id` bug; (3) "retraining pays because it adds data" — wrong, recency is
82%; (4) behavioural features would make explanations legible — 0 of the top 4
alerts cite one.

---

## 5. How to run

### 5.1 Setup

The project uses [`uv`](https://docs.astral.sh/uv/). Python 3.14; principal
dependencies `xgboost` · `lightgbm` · `scikit-learn` · `torch` · `pandas` ·
`pyarrow`.

```bash
uv sync
```

**Data is not in the repository** (gitignored — large, and separately licensed).
Place it here:

```text
datasets/creditcard.csv
datasets/ieeecis-fraud-detection/train_transaction.csv
datasets/ieeecis-fraud-detection/train_identity.csv
```

> Only the `train_*` tables of IEEE-CIS are usable. `test_transaction.csv` has
> **no `isFraud` column** — it is the Kaggle competition test set and its labels
> are held by the organisers. It also spans days 213–396, entirely *after* the
> training data (days 1–183), so it is unusable as extra training data too:
> training on it would be training on the future.

### 5.2 Mandatory first step — build the splits

Every experiment reads its splits from disk. Nothing runs without this.

```bash
uv run python scripts/build_splits.py --dataset creditcard
uv run python scripts/build_splits.py --dataset ieeecis
```

Writes `datasets/processed/<dataset>/{dev,holdout}.parquet` plus
`split_manifest.json`. Temporal-leakage checks run **before anything reaches
disk**, so a broken split cannot exist on the filesystem.

### 5.3 Run experiments

```bash
# One model
uv run python scripts/run_experiment.py --dataset ieeecis --model lightgbm_tuned

# Every model applicable to that dataset
uv run python scripts/run_experiment.py --dataset ieeecis --all
```

Writes `experiments/results/<dataset>/<model>/record.json` and `scores.npz`. **A
run is not complete until `scores.npz` is saved** — that is what
`compare_models.py` later pairs on (invariant IV).

### 5.4 Conclusions — always a paired test, never the leaderboard

```bash
uv run python scripts/compare_models.py --dataset ieeecis xgboost lightgbm_tuned
```

The script **refuses to run** if the two records were not scored on identical
rows.

### 5.5 Specialised measurements

```bash
# Profile a dataset before freezing its spec (entity proxies, duplicates, drift)
uv run python scripts/profile_dataset.py --dataset ieeecis

# Drift — three arms, recency/volume decomposition, paired test
uv run python scripts/drift_experiment.py --dataset ieeecis --model xgboost

# PU cascade — measure pseudo-label quality BEFORE trusting the cascade's AUPRC
uv run python scripts/pu_diagnostic.py --dataset ieeecis

# Explanation — attribution + counterfactual for the top alerts
uv run python scripts/explain_alerts.py --dataset ieeecis --model xgboost_behavioral --top 5

# Novel-fraud holdout (creditcard)
uv run python scripts/novel_fraud_experiment.py
```

### 5.6 Checks

```bash
uv run pytest                              # 366 tests
uv run python scripts/verify_migration.py  # migration constraint — see §6
```

---

## 6. Rules for whoever takes over

### Migration constraint — run after ANY change to layers 1–3

```bash
uv run python scripts/verify_migration.py   # must print 12/12
```

`xgboost` on creditcard must still produce **`0.7741`** with per-fold
`[0.8168, 0.6668, 0.8213, 0.7916]`. A single digit of drift means your change
moved behaviour somewhere — find it before continuing. This is the only test
that distinguishes "refactor" from "rewrite".

### The holdout is locked

The holdout has **never been scored** (0 of 37 records). Touching it requires the
explicit `--touch-holdout` flag. That barrier is deliberate: scoring it
repeatedly turns it into a second validation set.

### Adding a dataset

Add **one `DatasetSpec`** plus, if it brings genuinely new structure, **one
`FeatureGroup`**. Do not touch layers 5–10. If you must, a layer boundary has
been violated somewhere and the cause is worth finding.

### Adding a model

A model must declare: `label_regime` (which track), `scale_columns` (`"none"` is
a **positive claim** of scale invariance, not an omission), `handles_missing`,
and `requires_entity` if it needs per-entity history. The registry holds
**factories**, not instances — the runner builds a fresh model per fold.

### Known traps

**Behavioural features.** The intuitive spelling
`df.groupby(entity)[amount].transform("mean")` **sees the entity's future**. It
raises nothing and improves every number. Use strictly-prior expanding
aggregates.

**Composite entity keys.** `Series.astype(str)` **preserves NaN** in pandas 2.x —
one missing component nulls the whole identifier, and `pd.factorize` then pools
them into a single enormous entity. Fixed via `ENTITY_MISSING`, with a raising
guard in `_EntityView`.

**Background jobs.** An empty output file does **not** prove a job died — stdout
is buffered. Check the process. And do not run two memory-heavy jobs
concurrently on the 431-column dataset: `IsolationForest` densifies the DataFrame
into a >1 GB contiguous array.

**Comparisons across time.** Comparing a model to **itself at a different time**
cannot separate "the model changed" from "the problem changed", because time
blocks differ in intrinsic difficulty. Compare **two models on the same block**.

---

## 7. Outstanding work



### Done this session — five cheap measurements, all closing a real question

| # | Task | Result |
|---|---|---|
| 1 | Decay curve for `lightgbm_tuned` | Generalises (75%/25% recency-volume split) — **and** reveals the tuning gain is conditional: freezing erodes 61% of it |
| 2 | `card1` entity proxy | Behavioural-features-are-redundant conclusion **survives** a proxy test designed to refute it |
| 3 | Extend tuning to `logreg` | **Negative** — inconsistent 2-2 against the known best, after fixing two search-space bugs (see below) |
| 4 | `explain_alerts` on creditcard | The "PCA is unexplainable" claim is **confirmed** — first documented expectation to survive measurement |
| 5 | Sweep `train_blocks` | Corrects an earlier claim: saturates at width 2 (33% of data), not width 1 |

Two real bugs were found and fixed while running #3: `LOGREG_SPACE` initially
included `scale_columns`, which the runner resolves *before* `fit` and a
candidate's value is therefore never read — an inert search dimension that
silently halved the effective candidate count. Removing it left `TunedModel`
inheriting `scale_columns="default"` from the prototype, locking the search out
of the better-known scaling. Both are now guarded: `TuningError` fires at
construction if a search space names a runner-resolved parameter
(`INERT_IN_SEARCH` in `src/models/tuning.py`), and `logreg_tuned`'s factory
pins `scale_columns="all"` explicitly.

### Consider — scope expansion, decide before starting

**`PartialLabel`** — implemented and tested but **registered nowhere** (dead
code). It answers *"how much of the fraud needs labelling before performance
saturates"*, which has direct operational value. Not done because it needs a
`reveal_fraction` sweep — infrastructure for a family of runs, not a single
registry entry.

**Early stopping inside the tuning layer** — the original reason to avoid it (it
would create an undocumented second split) no longer applies now that the inner
validation slice is explicit. Needs its own measurement for the refit tree count.

### Already answered — do not redo

- **Raising `n_candidates` in the search** — the response surface is flat,
  measured across 4 seeds: four very different configurations produced nearly
  identical AUPRC. More sampling on a plateau finds nothing better.
- **Widening the autoencoder** — measured; the wide variant (`128→64→32`) is
  *worse* than the narrow one (`20→14→7`).

### Next phase — not started

Phase 2 (hybrid quantum layer) per the README roadmap. Note from diary_v2 §11:
**classical ML is the priority and must be optimised first**; quantum is an
experiment to answer *"what changes when quantum is available"*. One prediction
already follows from the classical results: a Quantum Autoencoder maximises
fidelity over the **whole** training set — structurally the same as a classical
AE minimising MSE — so the measured result (the AE losing 72% of its performance
to 0.17% contamination) **predicts a failure mode for QAE** deployed without
clean training data.
