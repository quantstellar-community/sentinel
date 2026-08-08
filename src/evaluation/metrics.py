"""Evaluation under extreme class imbalance.

AUPRC is the primary metric. The point of this module, though, is the interval
around it: a temporal holdout of this dataset contains roughly 50-75 fraud
cases, and an AUPRC computed on that many positives carries a confidence
interval wide enough to swallow most of the differences people report between
models. Every AUPRC produced here comes with a bootstrap CI so that claims of
improvement can be checked against sampling noise.

The AUPRC of a random ranker equals the positive rate — about 0.0017 here — so
`lift_over_random` is the honest way to state how far above chance a model is.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)

from src import config


class MetricError(ValueError):
    """Raised when a metric cannot be computed on the given inputs."""


@dataclass(frozen=True)
class EvaluationResult:
    """Everything needed to compare two models honestly."""

    n: int
    n_positive: int
    prevalence: float

    auprc: float
    auprc_ci_low: float
    auprc_ci_high: float
    lift_over_random: float

    roc_auc: float

    threshold: float
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    precision_at_k: dict[int, float] = field(default_factory=dict)
    recall_at_k: dict[int, float] = field(default_factory=dict)

    n_bootstrap: int = 0

    def to_dict(self) -> dict:
        out = asdict(self)
        # JSON object keys must be strings.
        out["precision_at_k"] = {str(k): v for k, v in self.precision_at_k.items()}
        out["recall_at_k"] = {str(k): v for k, v in self.recall_at_k.items()}
        return out

    def summary(self) -> str:
        """One-screen human summary, CI included so it cannot be quoted without."""
        lines = [
            f"n={self.n:,}  positives={self.n_positive}  prevalence={self.prevalence:.5f}",
            f"AUPRC        {self.auprc:.4f}  "
            f"[{self.auprc_ci_low:.4f}, {self.auprc_ci_high:.4f}] 95% CI"
            f"  ({self.lift_over_random:.0f}x random)",
            f"ROC-AUC      {self.roc_auc:.4f}",
            f"@thr={self.threshold:.4f}   precision={self.precision:.4f} "
            f"recall={self.recall:.4f} f1={self.f1:.4f}",
            f"             TP={self.true_positives} FP={self.false_positives} "
            f"FN={self.false_negatives} TN={self.true_negatives:,}",
        ]
        if self.precision_at_k:
            at_k = "  ".join(
                f"P@{k}={v:.3f}" for k, v in sorted(self.precision_at_k.items())
            )
            lines.append(f"alert budget {at_k}")
        return "\n".join(lines)


def _validate(y_true: np.ndarray, y_score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y_true = np.asarray(y_true).ravel()
    y_score = np.asarray(y_score, dtype=float).ravel()

    if y_true.shape != y_score.shape:
        raise MetricError(f"shape mismatch: y_true{y_true.shape} vs y_score{y_score.shape}")
    if y_true.size == 0:
        raise MetricError("empty input")
    if not np.isin(y_true, (0, 1)).all():
        raise MetricError("y_true must contain only 0 and 1")
    if not np.isfinite(y_score).all():
        raise MetricError("y_score contains NaN or inf")

    n_positive = int(y_true.sum())
    if n_positive == 0:
        raise MetricError("y_true contains no positives; AUPRC is undefined")
    if n_positive == y_true.size:
        raise MetricError("y_true contains no negatives; AUPRC is undefined")

    return y_true.astype(int), y_score


def _top_k(y_score: np.ndarray, k: int, n: int) -> np.ndarray:
    """Indices of the `k` highest scores, ties broken by original order.

    A stable sort rather than `argpartition`: tree ensembles produce many tied
    scores, and an arbitrary tie-break would make precision@k vary between runs
    on identical inputs.
    """
    if k <= 0:
        raise MetricError(f"k must be positive, got {k}")
    return np.argsort(-y_score, kind="stable")[: min(k, n)]


def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of the top-`k` highest-scored cases that are fraud.

    This is the metric an operations team actually feels: a review queue holds
    `k` alerts a day, and this is the share of that queue that is worth opening.
    """
    y_true, y_score = _validate(y_true, y_score)
    return float(y_true[_top_k(y_score, k, y_true.size)].sum() / min(k, y_true.size))


def recall_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Fraction of all fraud caught within the top-`k` highest-scored cases."""
    y_true, y_score = _validate(y_true, y_score)
    return float(y_true[_top_k(y_score, k, y_true.size)].sum() / y_true.sum())


def auprc_bootstrap_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    *,
    n_bootstrap: int | None = None,
    alpha: float | None = None,
    seed: int | None = None,
) -> tuple[float, float]:
    """Percentile bootstrap CI for AUPRC.

    Resamples cases with replacement. Resamples that happen to contain no
    positives are skipped rather than scored as zero, which would drag the lower
    bound down for a reason that has nothing to do with the model.
    """
    y_true, y_score = _validate(y_true, y_score)
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap
    alpha = config.BOOTSTRAP_ALPHA if alpha is None else alpha
    seed = config.SEED if seed is None else seed

    if n_bootstrap <= 0:
        return (float("nan"), float("nan"))

    rng = np.random.default_rng(seed)
    n = y_true.size
    scores: list[float] = []

    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        resampled_true = y_true[idx]
        if resampled_true.sum() == 0 or resampled_true.sum() == n:
            continue
        scores.append(average_precision_score(resampled_true, y_score[idx]))

    if not scores:
        return (float("nan"), float("nan"))

    low, high = np.percentile(scores, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(low), float(high))


@dataclass(frozen=True)
class ComparisonResult:
    """Paired comparison of two rankings of the same cases."""

    label_a: str
    label_b: str
    auprc_a: float
    auprc_b: float
    delta: float
    delta_ci_low: float
    delta_ci_high: float
    prob_b_better: float
    n_bootstrap: int

    @property
    def significant(self) -> bool:
        """True when the interval for the difference excludes zero."""
        return self.delta_ci_low > 0.0 or self.delta_ci_high < 0.0

    def to_dict(self) -> dict:
        return {**asdict(self), "significant": self.significant}

    def summary(self) -> str:
        verdict = (
            f"{self.label_b} beats {self.label_a}"
            if self.significant and self.delta > 0
            else f"{self.label_a} beats {self.label_b}"
            if self.significant
            else "no difference demonstrated"
        )
        return (
            f"{self.label_a}: {self.auprc_a:.4f}   {self.label_b}: {self.auprc_b:.4f}\n"
            f"delta {self.delta:+.4f}  "
            f"[{self.delta_ci_low:+.4f}, {self.delta_ci_high:+.4f}] 95% CI  "
            f"P(better)={self.prob_b_better:.3f}\n"
            f"verdict: {verdict}"
        )


def compare_auprc(
    y_true: np.ndarray,
    score_a: np.ndarray,
    score_b: np.ndarray,
    *,
    label_a: str = "A",
    label_b: str = "B",
    n_bootstrap: int | None = None,
    alpha: float | None = None,
    seed: int | None = None,
) -> ComparisonResult:
    """Paired bootstrap on the AUPRC *difference* between two models.

    This, not two overlapping confidence intervals, is how a claim of
    improvement should be tested. Both models are scored on the same resampled
    cases every iteration, so the variance they share — which cases happened to
    be drawn, how hard those cases are — cancels in the difference.

    The gain is largest exactly where it is needed: two models built on the same
    features agree on most cases, so their marginal intervals overlap heavily
    while the interval on their difference stays narrow. Note the condition,
    though — pairing helps because the two rankings are positively correlated.
    For models whose errors are unrelated the difference carries the sum of both
    variances and the paired interval is *wider*, not narrower.

    Use it for every classical-vs-quantum comparison the project reports: same
    split, same cases, difference measured pairwise.
    """
    y_true, score_a = _validate(y_true, score_a)
    _, score_b = _validate(y_true, score_b)

    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap
    alpha = config.BOOTSTRAP_ALPHA if alpha is None else alpha
    seed = config.SEED if seed is None else seed

    auprc_a = float(average_precision_score(y_true, score_a))
    auprc_b = float(average_precision_score(y_true, score_b))

    rng = np.random.default_rng(seed)
    n = y_true.size
    deltas: list[float] = []

    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        resampled_true = y_true[idx]
        if resampled_true.sum() == 0 or resampled_true.sum() == n:
            continue
        deltas.append(
            average_precision_score(resampled_true, score_b[idx])
            - average_precision_score(resampled_true, score_a[idx])
        )

    if not deltas:
        raise MetricError("every bootstrap resample was degenerate")

    delta_array = np.asarray(deltas)
    low, high = np.percentile(delta_array, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    return ComparisonResult(
        label_a=label_a,
        label_b=label_b,
        auprc_a=auprc_a,
        auprc_b=auprc_b,
        delta=auprc_b - auprc_a,
        delta_ci_low=float(low),
        delta_ci_high=float(high),
        prob_b_better=float((delta_array > 0).mean()),
        n_bootstrap=len(deltas),
    )


def best_f1_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Threshold maximizing F1 on the given data.

    Only ever call this on a *validation* split. Choosing a threshold on the
    holdout and then reporting metrics at that threshold is threshold leakage:
    the number stops being an out-of-sample estimate.
    """
    y_true, y_score = _validate(y_true, y_score)
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)

    # precision_recall_curve returns one more point than thresholds.
    precision, recall = precision[:-1], recall[:-1]
    denominator = precision + recall
    f1 = np.divide(
        2 * precision * recall,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator > 0,
    )
    if f1.size == 0:
        raise MetricError("could not compute a threshold: degenerate PR curve")
    return float(thresholds[int(np.argmax(f1))])


def evaluate(
    y_true: np.ndarray,
    y_score: np.ndarray,
    *,
    threshold: float | None = None,
    n_bootstrap: int | None = None,
    ks: tuple[int, ...] | None = None,
    seed: int | None = None,
) -> EvaluationResult:
    """Score a set of predictions against the Phase 0 evaluation contract.

    `threshold` should come from a validation split. If omitted it is chosen on
    the data being scored, which is fine for a sanity check and not fine for a
    reported result.
    """
    y_true, y_score = _validate(y_true, y_score)
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap
    ks = config.PRECISION_AT_K if ks is None else ks

    n = int(y_true.size)
    n_positive = int(y_true.sum())
    prevalence = n_positive / n

    auprc = float(average_precision_score(y_true, y_score))
    ci_low, ci_high = auprc_bootstrap_ci(
        y_true, y_score, n_bootstrap=n_bootstrap, seed=seed
    )

    if threshold is None:
        threshold = best_f1_threshold(y_true, y_score)

    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    precision = float(tp / (tp + fp)) if (tp + fp) else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return EvaluationResult(
        n=n,
        n_positive=n_positive,
        prevalence=prevalence,
        auprc=auprc,
        auprc_ci_low=ci_low,
        auprc_ci_high=ci_high,
        lift_over_random=auprc / prevalence,
        roc_auc=float(roc_auc_score(y_true, y_score)),
        threshold=float(threshold),
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=int(tp),
        false_positives=int(fp),
        true_negatives=int(tn),
        false_negatives=int(fn),
        precision_at_k={k: precision_at_k(y_true, y_score, k) for k in ks},
        recall_at_k={k: recall_at_k(y_true, y_score, k) for k in ks},
        n_bootstrap=n_bootstrap,
    )
