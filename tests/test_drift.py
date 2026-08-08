"""Layer 9 tests.

The decay curve is only interpretable if its first point is directly comparable
to the first fold of an ordinary run — both train on block 0 alone, so both must
produce the same number. Everything downstream is a *difference* between the two
arms, so a discrepancy there would silently become the thing being reported.

The other property is the usual one: a model measuring decay must never see the
blocks it is being decayed against.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.datasets import IEEECIS
from src.evaluation import drift, runner
from src.models import get_model
from tests.conftest import make_dev


def factory():
    return get_model("logreg", IEEECIS)


# --------------------------------------------------------------------------
# The construction check
# --------------------------------------------------------------------------


def test_the_first_block_matches_an_ordinary_run_exactly():
    """Both arms train on block 0 and score block 1, so they are the same
    computation. If this drifts, every reported gain is measuring the
    discrepancy rather than the passage of time."""
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)

    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    record = runner.run_cv(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    assert curve.auprcs[0] == pytest.approx(record.fold_auprcs[0], abs=1e-9)
    drift.assert_baseline_agrees(curve.auprcs[0], record.fold_auprcs[0])


def test_a_disagreeing_baseline_is_rejected():
    with pytest.raises(drift.DriftError, match="construction error"):
        drift.assert_baseline_agrees(0.50, 0.55)


def test_one_point_per_evaluation_block():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    assert len(curve.points) == IEEECIS.n_cv_folds
    assert [p.distance for p in curve.points] == list(range(1, IEEECIS.n_cv_folds + 1))
    assert all(p.n_positive > 0 for p in curve.points), (
        "a block with no fraud makes its AUPRC meaningless"
    )


# --------------------------------------------------------------------------
# Nothing may look forward
# --------------------------------------------------------------------------


def test_the_frozen_model_only_ever_trains_on_the_first_block():
    """The whole measurement rests on the model never being updated. A refit on
    a later block would turn the decay curve into a second expanding window."""
    seen: list[int] = []

    class Spy:
        name = "spy"

        def __init__(self):
            self._inner = get_model("logreg", IEEECIS)

        def __getattr__(self, item):
            return getattr(self._inner, item)

        def bind(self, spec):
            self._inner.bind(spec)
            return self

        def fit(self, X, y):
            seen.append(len(X))
            self._inner.fit(X, y)
            return self

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    drift.decay_curve(Spy, spec=IEEECIS, dev=dev, n_bootstrap=0)

    assert len(set(seen)) == 1, (
        f"the frozen arm trained on {sorted(set(seen))} different row counts; it "
        "must refit the same block every time"
    )


def test_training_rows_all_precede_every_evaluation_block():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    from src.data import splitter

    folds = splitter.expanding_window_folds(dev, IEEECIS)
    train_end = dev.iloc[folds[0].train_idx][IEEECIS.time_column].max()

    for fold, point in zip(folds, curve.points, strict=True):
        block_start = dev.iloc[fold.val_idx][IEEECIS.time_column].min()
        assert train_end < block_start, (
            f"block {point.block} starts at {block_start}, not after training "
            f"which ends at {train_end}"
        )


# --------------------------------------------------------------------------
# Pairing
# --------------------------------------------------------------------------


def test_retraining_gain_refuses_a_mismatched_arm():
    """Two arms of different lengths are not the same partition, so pairing them
    would produce a confident number about nothing."""
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    with pytest.raises(drift.DriftError, match="not the same partition"):
        curve.retraining_gain([0.5, 0.5])


def test_retraining_gain_is_the_difference_per_block():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    retrained = [a + 0.01 for a in curve.auprcs]
    assert curve.retraining_gain(retrained) == pytest.approx([0.01] * len(retrained))


def test_the_two_arms_are_scored_on_identical_rows():
    """Paired comparison at layer 8 requires it, and it is what makes the
    difference a difference rather than two unrelated measurements."""
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)

    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    record = runner.run_cv(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    for point, outcome in zip(curve.points, record.folds, strict=True):
        assert np.array_equal(point.y, outcome.val_y)


# --------------------------------------------------------------------------
# The sliding arm — what separates recency from volume
# --------------------------------------------------------------------------


def test_sliding_and_expanding_score_identical_rows():
    """The property that makes the decomposition a decomposition. If the two
    schemes evaluated on different rows, subtracting them would be comparing two
    unrelated measurements and calling the difference an effect."""
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    expanding = splitter.expanding_window_folds(dev, IEEECIS)
    sliding = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=1)

    for a, b in zip(expanding, sliding, strict=True):
        assert np.array_equal(a.val_idx, b.val_idx)


def test_the_sliding_window_keeps_a_constant_amount_of_training_data():
    """Volume held fixed is the entire mechanism. An expanding window grows from
    one block to six; this one must not."""
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    expanding = splitter.expanding_window_folds(dev, IEEECIS)
    sliding = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=1)

    widths = [len(f.train_idx) for f in sliding]
    assert max(widths) - min(widths) <= 0.05 * max(widths), (
        f"sliding training sizes vary too much: {widths}"
    )
    assert len(expanding[-1].train_idx) > 3 * len(sliding[-1].train_idx), (
        "the expanding arm should have accumulated much more by the last fold"
    )


def test_the_sliding_window_discards_the_oldest_rows():
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    sliding = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=1)
    last = sliding[-1]

    earliest_used = dev.iloc[last.train_idx][IEEECIS.time_column].min()
    assert earliest_used > dev[IEEECIS.time_column].min(), (
        "a sliding window that still contains the first row has discarded nothing"
    )


def test_fold_zero_is_identical_under_both_schemes():
    """Nothing has been discarded yet at fold 0, so the two partitions must
    agree there. A free check that they are the same partition."""
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    expanding = splitter.expanding_window_folds(dev, IEEECIS)
    sliding = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=1)

    assert np.array_equal(expanding[0].train_idx, sliding[0].train_idx)


def test_a_wider_sliding_window_keeps_more_history():
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    narrow = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=1)
    wide = splitter.sliding_window_folds(dev, IEEECIS, train_blocks=3)

    assert len(wide[-1].train_idx) > len(narrow[-1].train_idx)


def test_a_zero_width_window_is_rejected():
    from src.data import splitter

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    with pytest.raises(splitter.SplitError, match="train_blocks"):
        splitter.sliding_window_folds(dev, IEEECIS, train_blocks=0)


def test_the_decomposition_sums_to_the_total():
    """recency + volume == total, by construction. Worth pinning: the whole
    claim is that the retraining gain splits cleanly into these two."""
    frozen = [0.40, 0.42, 0.41]
    sliding = [0.40, 0.45, 0.46]
    expanding = [0.40, 0.50, 0.52]

    parts = drift.decompose(frozen, sliding, expanding)

    for i in range(3):
        assert parts["recency"][i] + parts["volume"][i] == pytest.approx(
            parts["total"][i]
        )


def test_the_decomposition_refuses_mismatched_arms():
    with pytest.raises(drift.DriftError, match="not the same partition"):
        drift.decompose([0.1, 0.2], [0.1], [0.1, 0.2])


def test_the_sliding_arm_trains_on_a_fixed_width_every_fold():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.sliding_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    widths = [p.n_train for p in curve.points]
    assert max(widths) - min(widths) <= 0.05 * max(widths), widths
    assert all(p.distance == 1 for p in curve.points), (
        "a sliding window is always one block behind its evaluation block"
    )


# --------------------------------------------------------------------------
# Invariant IV — scores must outlive the run
# --------------------------------------------------------------------------


def test_both_arms_persist_their_raw_scores(tmp_path):
    """PIPELINE_V2 invariant IV. An earlier version of this layer saved only the
    AUPRCs, which left the decomposition untestable: a paired bootstrap needs
    the scores, and recomputing them later is what the invariant forbids."""
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    frozen = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    sliding = drift.sliding_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    path = drift.save_scores(frozen, sliding, tmp_path)

    with np.load(path) as stored:
        for point in frozen.points:
            assert np.array_equal(
                stored[f"frozen_block{point.block}_scores"], point.scores
            )
            assert np.array_equal(stored[f"frozen_block{point.block}_y"], point.y)
        for point in sliding.points:
            assert np.array_equal(
                stored[f"sliding_block{point.block}_scores"], point.scores
            )


def test_the_decomposition_can_be_tested_pairwise():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    frozen = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    sliding = drift.sliding_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    record = runner.run_cv(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    expanding = {o.fold: (o.val_scores, o.val_y) for o in record.folds}

    paired = drift.paired_decomposition(
        frozen, sliding, expanding, n_bootstrap=50, seed=0
    )

    assert len(paired) == len(frozen.points)
    for entry in paired:
        assert entry["recency"].label_b == "sliding"
        assert entry["volume"].label_b == "expanding"


def test_the_paired_decomposition_refuses_arms_scored_on_different_rows():
    """Three arms on different rows would still produce a confident number."""
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    frozen = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    sliding = drift.sliding_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    corrupted = {
        i: (p.scores, 1 - p.y)  # same rows, different labels
        for i, p in enumerate(frozen.points)
    }
    with pytest.raises(drift.DriftError, match="different rows"):
        drift.paired_decomposition(frozen, sliding, corrupted, n_bootstrap=10)


def test_the_paired_decomposition_refuses_a_missing_fold():
    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    frozen = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    sliding = drift.sliding_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)

    with pytest.raises(drift.DriftError, match="different partition"):
        drift.paired_decomposition(frozen, sliding, {}, n_bootstrap=10)


def test_the_payload_is_json_serializable():
    import json

    dev = make_dev(IEEECIS, n=3_000, n_unique_times=1_500)
    curve = drift.decay_curve(factory, spec=IEEECIS, dev=dev, n_bootstrap=0)
    json.dumps(curve.to_dict())
