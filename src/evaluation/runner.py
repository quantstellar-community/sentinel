"""The single path from a model to a recorded result.

Two things this module does that a per-model script would not:

* **It keeps the raw validation scores.** A comparison between two models has to
  be paired on identical cases, so the scores must outlive the run that produced
  them. Recomputing them later from a saved model is not the same thing — it
  reintroduces every version and seed difference the pairing exists to remove.
* **It re-derives the folds from the manifest every time.** No experiment gets
  to define its own split.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src import __version__, config
from src.data import loader, splitter
from src.data.preprocessor import Preprocessor
from src.datasets import DEV_SPLIT_NAME, HOLDOUT_SPLIT_NAME, DatasetSpec, get_spec
from src.evaluation import metrics
from src.features import FeaturePipeline, default_pipeline
from src.models.base import SentinelModel
from src.models.regime import LabelRegimeError


class ExperimentError(RuntimeError):
    """Raised when a run cannot be recorded honestly."""


@dataclass
class FoldOutcome:
    """One fold's result plus the scores needed to compare it with another run."""

    fold: int
    n_train: int
    n_train_fraud: int
    result: metrics.EvaluationResult
    val_scores: np.ndarray = field(repr=False)
    val_y: np.ndarray = field(repr=False)
    threshold_from_this_fold: float
    fit_seconds: float
    score_seconds: float
    resolution_warning: str | None = None

    @property
    def n_distinct_scores(self) -> int:
        return int(np.unique(self.val_scores).size)

    def to_dict(self) -> dict:
        return {
            "fold": self.fold,
            "n_train": self.n_train,
            "n_train_fraud": self.n_train_fraud,
            "n_distinct_scores": self.n_distinct_scores,
            "resolution_warning": self.resolution_warning,
            "fit_seconds": round(self.fit_seconds, 3),
            "score_seconds": round(self.score_seconds, 3),
            "score_microseconds_per_row": round(
                1e6 * self.score_seconds / max(len(self.val_scores), 1), 2
            ),
            **self.result.to_dict(),
        }


@dataclass
class ExperimentRecord:
    """Everything docs/evaluation_protocol.md §5 requires, in one object."""

    dataset: str
    model: dict
    created_at: str
    sentinel_version: str
    seed: int
    n_features: int
    n_bootstrap: int
    split_manifest_created_at: str
    source_sha256: str
    feature_pipeline: dict
    folds: list[FoldOutcome] = field(repr=False)
    holdout: metrics.EvaluationResult | None = None

    @property
    def name(self) -> str:
        return self.model["name"]

    @property
    def fold_auprcs(self) -> list[float]:
        return [outcome.result.auprc for outcome in self.folds]

    @property
    def mean_auprc(self) -> float:
        return float(np.mean(self.fold_auprcs))

    @property
    def mean_ci_width(self) -> float:
        return float(
            np.mean([o.result.auprc_ci_high - o.result.auprc_ci_low for o in self.folds])
        )

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "model": self.model,
            "created_at": self.created_at,
            "sentinel_version": self.sentinel_version,
            "seed": self.seed,
            "n_features": self.n_features,
            "n_bootstrap": self.n_bootstrap,
            "split_manifest_created_at": self.split_manifest_created_at,
            "source_sha256": self.source_sha256,
            "feature_pipeline": self.feature_pipeline,
            "mean_auprc": self.mean_auprc,
            "auprc_sd": float(np.std(self.fold_auprcs, ddof=1)) if len(self.folds) > 1 else 0.0,
            "mean_ci_width": self.mean_ci_width,
            "fold_auprcs": self.fold_auprcs,
            "folds": [outcome.to_dict() for outcome in self.folds],
            "holdout": self.holdout.to_dict() if self.holdout else None,
        }

    def summary(self) -> str:
        lines = [f"{self.name}: mean AUPRC {self.mean_auprc:.4f}"]
        for outcome in self.folds:
            r = outcome.result
            lines.append(
                f"  fold {outcome.fold}  AUPRC {r.auprc:.4f} "
                f"[{r.auprc_ci_low:.4f}, {r.auprc_ci_high:.4f}]  "
                f"ROC-AUC {r.roc_auc:.4f}  P@100 {r.precision_at_k.get(100, float('nan')):.3f}  "
                f"({r.n_positive} positives, fit {outcome.fit_seconds:.1f}s)"
            )
        return "\n".join(lines)


def _fit_and_score(
    model: SentinelModel,
    train: pd.DataFrame,
    evaluate_on: pd.DataFrame,
    spec: DatasetSpec,
    pipeline: FeaturePipeline,
):
    """Fit on `train`, score `evaluate_on`. Returns scores and timings.

    The order below is the leakage guarantee. Feature pipeline, feature budget,
    imputer and scaler are all resolved and fitted against `train` alone,
    before the model sees anything at all.
    """
    pipeline.fit(train)
    X_train = pipeline.transform(train)
    X_eval = pipeline.transform(evaluate_on)
    y_train = train[spec.target_column]
    y_eval = evaluate_on[spec.target_column]

    # Honour the model's declared feature budget rather than handing every model
    # every column and trusting it to use only what it said it would.
    columns = model.select_features(list(X_train.columns), spec)
    X_train, X_eval = X_train[columns], X_eval[columns]

    scale_columns = model.resolve_scale_columns(columns, spec)
    impute = not model.handles_missing
    if scale_columns or impute:
        pre = Preprocessor(columns=scale_columns, impute=impute).fit(X_train)
        X_train, X_eval = pre.transform(X_train), pre.transform(X_eval)

    # The label gate. Everything above this line is blind to y; everything
    # below sees only what the regime allows through. True labels reappear at
    # evaluation and nowhere else.
    if model.supervised and not model.label_regime.sees_labels:
        if not model.generates_own_labels:
            raise LabelRegimeError(
                f"{model.name} is supervised but declares the "
                f"{model.label_regime.name!r} regime, which reveals no labels. "
                "A supervised model in track C needs generates_own_labels=True "
                "and a step that manufactures them."
            )
    X_train, y_train = model.label_regime.apply(X_train, y_train)

    started = time.perf_counter()
    model.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - started

    started = time.perf_counter()
    scores = np.asarray(model.risk_score(X_eval), dtype=float)
    score_seconds = time.perf_counter() - started

    if scores.shape != (len(X_eval),):
        raise ExperimentError(
            f"{model.name}.risk_score returned shape {scores.shape}, expected ({len(X_eval)},)"
        )
    if not np.isfinite(scores).all():
        raise ExperimentError(f"{model.name}.risk_score returned NaN or inf")

    return (
        scores,
        y_eval.to_numpy(),
        fit_seconds,
        score_seconds,
        len(X_train),
        pipeline.output_columns(),
    )


#: Below this ratio of distinct scores to rows, ranking metrics stop measuring
#: the model and start measuring the tie-break. Chosen from a real failure: a
#: LightGBM run with no L2 penalty produced 65 distinct scores across 45,397
#: rows (0.0014) and its AUPRC fell to the random floor while ROC-AUC still
#: read 0.80. Anything of that shape must be visible, not averaged into a table.
MIN_DISTINCT_SCORE_RATIO = 0.01


def score_resolution_warning(scores: np.ndarray, y: np.ndarray) -> str | None:
    """Describe a degenerate score distribution, or return None if it is fine.

    A saturated model still produces a plausible-looking ROC-AUC, so this cannot
    be left to the metrics to reveal.
    """
    n = scores.size
    n_distinct = int(np.unique(scores).size)
    if n == 0 or n_distinct / n >= MIN_DISTINCT_SCORE_RATIO:
        return None

    top_value = scores.max()
    tied_at_top = scores >= top_value
    n_tied = int(tied_at_top.sum())
    fraud_in_tie = int(y[tied_at_top].sum())

    return (
        f"only {n_distinct:,} distinct scores across {n:,} rows "
        f"({n_distinct / n:.4f}); {n_tied:,} rows tie at the maximum, "
        f"{fraud_in_tie} of them fraud. Ranking metrics are measuring the "
        "tie-break, not the model — check regularisation and class weighting."
    )


def pipeline_for(
    model: SentinelModel,
    spec: DatasetSpec,
    override: FeaturePipeline | None = None,
) -> FeaturePipeline:
    """The feature pipeline one run uses.

    Precedence: an explicit `pipeline=` argument, then the model's own
    declaration, then the structural default. A fresh pipeline is built per fold
    rather than shared, so no group can carry state — a fitted encoder
    vocabulary, an entity's stored history — from one fold's training set into
    the next.
    """
    if override is not None:
        return override
    groups = model.feature_groups()
    return default_pipeline(spec) if groups is None else FeaturePipeline(groups, spec)


def run_cv(
    model_factory,
    *,
    spec: DatasetSpec | str | None = None,
    pipeline: FeaturePipeline | None = None,
    dev: pd.DataFrame | None = None,
    manifest: dict | None = None,
    n_bootstrap: int | None = None,
    n_folds: int | None = None,
) -> ExperimentRecord:
    """Run a model across the expanding-window folds and record the result."""
    spec = get_spec(spec)
    if dev is None:
        dev = loader.load_split(DEV_SPLIT_NAME, spec)
        manifest = loader.read_manifest(spec) if manifest is None else manifest
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap

    folds = splitter.expanding_window_folds(dev, spec, n_folds=n_folds)
    outcomes: list[FoldOutcome] = []
    declaration = None
    fold_pipeline: FeaturePipeline | None = None

    for fold in folds:
        train, val = dev.iloc[fold.train_idx], dev.iloc[fold.val_idx]
        splitter.assert_no_temporal_leakage(train, val, spec)

        model = model_factory().bind(spec)
        fold_pipeline = pipeline_for(model, spec, pipeline)

        scores, y_val, fit_s, score_s, n_train, available = _fit_and_score(
            model, train, val, spec, fold_pipeline
        )
        declaration = model.describe(available, spec)
        result = metrics.evaluate(y_val, scores, n_bootstrap=n_bootstrap, seed=config.SEED)

        warning = score_resolution_warning(scores, y_val)
        if warning:
            print(f"  WARNING  {model.name} fold {fold.index}: {warning}")

        outcomes.append(
            FoldOutcome(
                fold=fold.index,
                n_train=n_train,
                n_train_fraud=fold.train_stats.n_fraud,
                result=result,
                val_scores=scores,
                val_y=y_val,
                threshold_from_this_fold=metrics.best_f1_threshold(y_val, scores),
                fit_seconds=fit_s,
                score_seconds=score_s,
                resolution_warning=warning,
            )
        )

    if declaration is None or fold_pipeline is None:
        raise ExperimentError("no folds were produced")

    return ExperimentRecord(
        dataset=spec.name,
        model=declaration,
        created_at=datetime.now(timezone.utc).isoformat(),
        sentinel_version=__version__,
        seed=config.SEED,
        n_features=declaration["n_features"],
        n_bootstrap=n_bootstrap,
        split_manifest_created_at=(manifest or {}).get("created_at", ""),
        source_sha256=(manifest or {}).get("source", {}).get("sha256", ""),
        feature_pipeline=fold_pipeline.describe(),
        folds=outcomes,
    )


def score_holdout(
    model_factory,
    record: ExperimentRecord,
    *,
    spec: DatasetSpec | str | None = None,
    pipeline: FeaturePipeline | None = None,
    n_bootstrap: int | None = None,
) -> metrics.EvaluationResult:
    """Fit on all of dev and score the locked holdout, once.

    The threshold is carried over from the last validation fold. Choosing it on
    the holdout would make the reported precision and recall in-sample.
    """
    spec = get_spec(spec)
    dev = loader.load_split(DEV_SPLIT_NAME, spec)
    holdout = loader.load_split(HOLDOUT_SPLIT_NAME, spec)
    splitter.assert_no_temporal_leakage(dev, holdout, spec)

    model = model_factory().bind(spec)
    scores, y_holdout, _, _, _, _ = _fit_and_score(
        model, dev, holdout, spec, pipeline_for(model, spec, pipeline)
    )

    result = metrics.evaluate(
        y_holdout,
        scores,
        threshold=record.folds[-1].threshold_from_this_fold,
        n_bootstrap=config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap,
        seed=config.SEED,
    )
    record.holdout = result
    return result


# --------------------------------------------------------------------------
# Persistence
#
# The record is JSON so it can be read; the scores are npz because storing
# ~180,000 floats as JSON text would make the record unreadable for no gain.
# --------------------------------------------------------------------------


def result_dir(name: str, spec: DatasetSpec | str | None = None) -> Path:
    """Results are namespaced by dataset.

    Two runs of the same model name on different datasets must never be paired
    against each other; separate trees make that mistake hard to make by
    accident.
    """
    return get_spec(spec).results_dir / name


def save(record: ExperimentRecord) -> Path:
    """Write the record and its per-fold scores under experiments/results/<name>/."""
    directory = result_dir(record.name, record.dataset)
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "record.json").write_text(
        json.dumps(record.to_dict(), indent=2), encoding="utf-8"
    )

    arrays: dict[str, np.ndarray] = {}
    for outcome in record.folds:
        arrays[f"fold{outcome.fold}_scores"] = outcome.val_scores
        arrays[f"fold{outcome.fold}_y"] = outcome.val_y
    np.savez_compressed(directory / "scores.npz", **arrays)

    return directory


def load_scores(
    name: str, spec: DatasetSpec | str | None = None
) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Read back `{fold: (scores, y)}` for a previously saved run."""
    resolved = get_spec(spec)
    path = result_dir(name, resolved) / "scores.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: uv run python scripts/run_experiment.py "
            f"--dataset {resolved.name} --model {name}"
        )

    with np.load(path) as data:
        folds = sorted({int(key.split("_")[0].removeprefix("fold")) for key in data.files})
        return {i: (data[f"fold{i}_scores"], data[f"fold{i}_y"]) for i in folds}


def run_and_report(
    name: str,
    *,
    spec: DatasetSpec | str | None = None,
    pipeline: FeaturePipeline | None = None,
    n_bootstrap: int | None = None,
    touch_holdout: bool = False,
) -> ExperimentRecord:
    """Run a registered model, print the report, and persist it.

    Lives here rather than in a script so that both entry points share it —
    two scripts printing their own version of the same result is how numbers
    start disagreeing with each other.
    """
    from src.models import MODEL_REGISTRY, get_model

    spec = get_spec(spec)
    if name not in MODEL_REGISTRY:
        raise KeyError(f"unknown model {name!r}; available: {sorted(MODEL_REGISTRY)}")

    get_model(name, spec)  # fails fast if the model needs entity data this dataset lacks
    factory = MODEL_REGISTRY[name]

    print(f"\n{'=' * 72}\n{spec.name} / {name}\n{'=' * 72}")
    record = run_cv(factory, spec=spec, pipeline=pipeline, n_bootstrap=n_bootstrap)

    scaled = record.model["scale_columns"]
    regime = record.model["label_regime"]
    print(f"scaling: {scaled if scaled else 'none (model is scale-invariant)'}")
    print(f"track  : {regime['track']} — {regime['name']}")
    if regime["filters_to_normal"]:
        fits_on = "normal class only (labels used to filter, not in the loss)"
    elif not regime["sees_labels"]:
        fits_on = "all rows, no labels — training keeps its real contamination"
    else:
        fits_on = "all rows, labels in the loss"
    print(f"fits on: {fits_on}\n")
    print(record.summary())
    print(
        f"\nmean AUPRC {record.mean_auprc:.4f}   "
        f"per-fold {[round(a, 4) for a in record.fold_auprcs]}   "
        f"mean CI width {record.mean_ci_width:.4f}"
    )

    if touch_holdout:
        print("\n*** scoring the locked holdout ***")
        print(
            score_holdout(
                factory, record, spec=spec, pipeline=pipeline, n_bootstrap=n_bootstrap
            ).summary()
        )
    else:
        print("\nholdout not touched (pass --touch-holdout to score it).")

    print(f"\nwrote {save(record)}")
    return record


def load_record(name: str, spec: DatasetSpec | str | None = None) -> dict:
    resolved = get_spec(spec)
    path = result_dir(name, resolved) / "record.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: uv run python scripts/run_experiment.py "
            f"--dataset {resolved.name} --model {name}"
        )
    return json.loads(path.read_text(encoding="utf-8"))
