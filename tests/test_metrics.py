"""Metric correctness, with emphasis on the properties the protocol relies on."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import average_precision_score

from src.evaluation import metrics


def imbalanced(n: int = 5_000, n_positive: int = 60, *, separation: float = 2.0, seed: int = 0):
    """Labels and scores with roughly this dataset's prevalence and signal."""
    rng = np.random.default_rng(seed)
    y = np.zeros(n, dtype=int)
    y[rng.choice(n, size=n_positive, replace=False)] = 1
    score = rng.normal(size=n) + separation * y
    return y, score


# --------------------------------------------------------------------------
# Ranking metrics
# --------------------------------------------------------------------------


def test_perfect_ranking_scores_one():
    y = np.array([0, 0, 0, 1, 1])
    score = np.array([0.1, 0.2, 0.3, 0.9, 0.95])

    result = metrics.evaluate(y, score, n_bootstrap=0)
    assert result.auprc == pytest.approx(1.0)
    assert result.roc_auc == pytest.approx(1.0)


def test_random_ranking_approaches_prevalence():
    """The floor for AUPRC is the positive rate, not 0.5. This is why accuracy
    and ROC-AUC both mislead at 0.17% prevalence."""
    y, _ = imbalanced(n=20_000, n_positive=40)
    rng = np.random.default_rng(1)
    noise = rng.random(y.size)

    auprc = average_precision_score(y, noise)
    prevalence = y.mean()
    assert auprc == pytest.approx(prevalence, abs=0.004)


def test_precision_at_k_counts_the_review_queue():
    y = np.array([1, 1, 0, 0, 1, 0, 0, 0])
    score = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2])

    assert metrics.precision_at_k(y, score, 2) == pytest.approx(1.0)
    assert metrics.precision_at_k(y, score, 4) == pytest.approx(0.5)
    assert metrics.recall_at_k(y, score, 2) == pytest.approx(2 / 3)
    assert metrics.recall_at_k(y, score, 5) == pytest.approx(1.0)


def test_precision_at_k_is_deterministic_under_ties():
    """Tree ensembles produce many tied scores; the metric must not wobble."""
    y = np.array([0, 1] * 50)
    score = np.full(100, 0.5)

    values = {metrics.precision_at_k(y, score, 10) for _ in range(5)}
    assert len(values) == 1


def test_k_larger_than_the_dataset_is_clamped():
    y, score = imbalanced(n=100, n_positive=10)
    assert metrics.recall_at_k(y, score, 10_000) == pytest.approx(1.0)


# --------------------------------------------------------------------------
# Bootstrap interval — the point of the module
# --------------------------------------------------------------------------


def test_ci_brackets_the_point_estimate():
    y, score = imbalanced()
    point = average_precision_score(y, score)
    low, high = metrics.auprc_bootstrap_ci(y, score, n_bootstrap=300, seed=0)

    assert low <= point <= high


def test_ci_is_reproducible_for_a_given_seed():
    y, score = imbalanced()
    first = metrics.auprc_bootstrap_ci(y, score, n_bootstrap=200, seed=7)
    second = metrics.auprc_bootstrap_ci(y, score, n_bootstrap=200, seed=7)

    assert first == second


def test_ci_widens_as_positives_get_scarcer():
    """The finding that motivates the whole protocol: with ~60 positives the
    interval is wide enough to swallow most reported model differences."""
    many_y, many_score = imbalanced(n=5_000, n_positive=600, seed=3)
    few_y, few_score = imbalanced(n=5_000, n_positive=60, seed=3)

    wide = metrics.auprc_bootstrap_ci(few_y, few_score, n_bootstrap=300, seed=0)
    narrow = metrics.auprc_bootstrap_ci(many_y, many_score, n_bootstrap=300, seed=0)

    assert (wide[1] - wide[0]) > (narrow[1] - narrow[0])


# --------------------------------------------------------------------------
# Paired comparison — the primitive every classical-vs-quantum claim rests on
# --------------------------------------------------------------------------


def test_identical_rankings_show_no_difference():
    y, score = imbalanced()
    result = metrics.compare_auprc(y, score, score, n_bootstrap=200, seed=0)

    assert result.delta == pytest.approx(0.0)
    assert not result.significant


def test_a_clearly_better_model_is_detected():
    y, weak = imbalanced(separation=0.5, seed=5)
    rng = np.random.default_rng(5)
    strong = rng.normal(size=y.size) + 3.0 * y

    result = metrics.compare_auprc(y, weak, strong, n_bootstrap=400, seed=0)
    assert result.delta > 0
    assert result.significant and result.delta_ci_low > 0
    assert result.prob_b_better > 0.95


def test_pairing_resolves_a_difference_that_overlapping_intervals_hide():
    """The reason `compare_auprc` exists.

    Two competing models built on the same features agree on most cases and
    differ on a few. Their marginal AUPRC intervals overlap heavily, so reading
    those intervals says "no difference". The paired test isolates the part
    where they actually disagree and resolves it.
    """
    y, weak = imbalanced(n=5_000, n_positive=60, separation=1.5, seed=11)
    strong = weak + 0.6 * y  # same noise, slightly better ranking

    ci_weak = metrics.auprc_bootstrap_ci(y, weak, n_bootstrap=400, seed=0)
    ci_strong = metrics.auprc_bootstrap_ci(y, strong, n_bootstrap=400, seed=0)
    paired = metrics.compare_auprc(y, weak, strong, n_bootstrap=400, seed=0)

    # The naive comparison is inconclusive: the intervals overlap.
    assert ci_weak[1] > ci_strong[0]

    # The paired comparison is not, and its interval is far tighter.
    paired_width = paired.delta_ci_high - paired.delta_ci_low
    marginal_width = min(ci_weak[1] - ci_weak[0], ci_strong[1] - ci_strong[0])
    assert paired_width < marginal_width
    assert paired.significant and paired.delta > 0


def test_pairing_does_not_help_for_uncorrelated_models():
    """The honest limit of the method: pairing cancels shared variance, so it
    buys nothing when two models make unrelated errors. Documented here so the
    tighter-interval property is never assumed unconditionally."""
    y, a = imbalanced(n=5_000, n_positive=60, separation=1.5, seed=11)
    rng = np.random.default_rng(99)
    b = rng.normal(size=y.size) + 1.5 * y  # independent noise, equal strength

    ci_a = metrics.auprc_bootstrap_ci(y, a, n_bootstrap=400, seed=0)
    paired = metrics.compare_auprc(y, a, b, n_bootstrap=400, seed=0)

    assert (paired.delta_ci_high - paired.delta_ci_low) > (ci_a[1] - ci_a[0])


def test_comparison_is_antisymmetric():
    y, a = imbalanced(seed=2)
    rng = np.random.default_rng(2)
    b = rng.normal(size=y.size) + 2.5 * y

    forward = metrics.compare_auprc(y, a, b, n_bootstrap=200, seed=0)
    backward = metrics.compare_auprc(y, b, a, n_bootstrap=200, seed=0)

    assert forward.delta == pytest.approx(-backward.delta)
    assert forward.significant == backward.significant


def test_comparison_serializes():
    import json

    y, score = imbalanced()
    payload = metrics.compare_auprc(y, score, score, n_bootstrap=50).to_dict()
    json.dumps(payload)
    assert "significant" in payload


# --------------------------------------------------------------------------
# Thresholds and reporting
# --------------------------------------------------------------------------


def test_confusion_counts_agree_with_the_threshold():
    y, score = imbalanced(n=2_000, n_positive=40)
    result = metrics.evaluate(y, score, threshold=1.0, n_bootstrap=0)

    predicted = (score >= 1.0).astype(int)
    assert result.true_positives == int(((predicted == 1) & (y == 1)).sum())
    assert result.false_positives == int(((predicted == 1) & (y == 0)).sum())
    assert result.false_negatives == int(((predicted == 0) & (y == 1)).sum())
    assert result.true_negatives == int(((predicted == 0) & (y == 0)).sum())


def test_lift_states_the_gain_over_chance():
    y, score = imbalanced()
    result = metrics.evaluate(y, score, n_bootstrap=0)

    assert result.lift_over_random == pytest.approx(result.auprc / result.prevalence)
    assert result.lift_over_random > 1.0


def test_result_serializes_to_json_safe_types():
    import json

    y, score = imbalanced()
    payload = metrics.evaluate(y, score, n_bootstrap=50).to_dict()

    json.dumps(payload)  # raises if a numpy scalar or int key slipped through
    assert all(isinstance(k, str) for k in payload["precision_at_k"])


def test_summary_always_reports_the_interval():
    y, score = imbalanced()
    text = metrics.evaluate(y, score, n_bootstrap=50).summary()

    assert "AUPRC" in text and "95% CI" in text


# --------------------------------------------------------------------------
# Guard rails
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("y", "score", "match"),
    [
        (np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3]), "no positives"),
        (np.array([1, 1, 1]), np.array([0.1, 0.2, 0.3]), "no negatives"),
        (np.array([0, 1]), np.array([0.1, np.nan]), "NaN"),
        (np.array([0, 2]), np.array([0.1, 0.2]), "only 0 and 1"),
        (np.array([0, 1, 0]), np.array([0.1, 0.2]), "shape mismatch"),
        (np.array([]), np.array([]), "empty"),
    ],
)
def test_invalid_inputs_raise(y, score, match):
    with pytest.raises(metrics.MetricError, match=match):
        metrics.evaluate(y, score, n_bootstrap=0)
