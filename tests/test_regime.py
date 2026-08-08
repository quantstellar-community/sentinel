"""Layer 5 tests.

The property that matters most: a track C model must be unable to reach the
labels, not merely trusted not to look. Everything else in this file supports
that one claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import CREDITCARD, IEEECIS
from src.evaluation import runner
from src.models import MODEL_REGISTRY, get_model, models_by_track, models_for
from src.models.base import SentinelModel
from src.models.regime import (
    FULLY_SUPERVISED,
    ONE_CLASS,
    UNLABELED,
    FullySupervised,
    LabelRegimeError,
    OneClass,
    PartialLabel,
    Unlabeled,
)
from tests.conftest import make_dev


@pytest.fixture
def labelled():
    X = pd.DataFrame({"a": range(10), "b": range(10, 20)})
    y = pd.Series([0, 0, 0, 0, 0, 0, 0, 1, 1, 1], name="Class")
    return X, y


# --------------------------------------------------------------------------
# The three regimes
# --------------------------------------------------------------------------


def test_track_a_passes_everything_through(labelled):
    X, y = labelled
    X_out, y_out = FullySupervised().apply(X, y)

    pd.testing.assert_frame_equal(X_out, X)
    pd.testing.assert_series_equal(y_out, y)


def test_track_b_keeps_only_the_normal_class(labelled):
    X, y = labelled
    X_out, y_out = OneClass().apply(X, y)

    assert len(X_out) == 7
    assert (y_out == 0).all()
    assert y_out.sum() == 0


def test_track_b_still_consumes_label_information():
    """Filtering to the normal class *uses* labels — someone had to know which
    rows were fraud in order to drop them. Calling it unsupervised is the
    confusion this layer exists to remove."""
    assert ONE_CLASS.sees_labels is True
    assert ONE_CLASS.filters_to_normal is True
    assert ONE_CLASS.track == "B"


def test_track_c_reveals_nothing(labelled):
    X, y = labelled
    X_out, y_out = Unlabeled().apply(X, y)

    # Every row survives — training keeps its real contamination.
    assert len(X_out) == len(X)
    # And the target carries no information at all.
    assert y_out.nunique() == 1
    assert y_out.sum() == 0


def test_track_c_labels_are_not_the_truth(labelled):
    """The blind target is a placeholder, not a claim that nothing is fraud."""
    X, y = labelled
    _, y_out = Unlabeled().apply(X, y)

    assert y.sum() == 3, "the fixture does contain fraud"
    assert y_out.sum() == 0, "but the model is told nothing about it"
    assert UNLABELED.sees_labels is False


def test_one_class_on_an_all_fraud_fold_raises(labelled):
    X, y = labelled
    with pytest.raises(LabelRegimeError, match="no normal rows"):
        OneClass().apply(X, pd.Series(1, index=y.index))


# --------------------------------------------------------------------------
# The runner-level guarantee
# --------------------------------------------------------------------------


def test_a_track_c_model_never_receives_a_positive_label():
    """The claim, checked end to end through the runner.

    A spy records every `y` it is handed during fitting. Under track C those
    must contain no positives at all, while the evaluation folds demonstrably
    do — which is what makes "run blind, score against the truth" a measurement
    rather than a hope.
    """
    seen: list[int] = []

    class Spy(SentinelModel):
        name = "spy_track_c"
        scale_columns = "none"
        handles_missing = True
        supervised = False
        label_regime = UNLABELED

        def fit(self, X, y):
            seen.append(int(np.asarray(y).sum()))
            return self

        def risk_score(self, X):
            return np.linspace(0, 1, len(X))

        def params(self):
            return {}

    dev = make_dev(CREDITCARD)
    record = runner.run_cv(Spy, dev=dev, n_bootstrap=0, n_folds=2)

    assert seen == [0, 0], f"a track C model was shown positives: {seen}"
    assert all(outcome.val_y.sum() > 0 for outcome in record.folds), (
        "the evaluation folds must contain fraud, or the test proves nothing"
    )


def test_a_track_c_model_trains_on_the_contaminated_rows():
    """Track C is not track B with the labels hidden — the fraud rows stay in."""
    sizes: list[int] = []

    class Spy(SentinelModel):
        name = "spy_size"
        scale_columns = "none"
        handles_missing = True
        supervised = False
        label_regime = UNLABELED

        def fit(self, X, y):
            sizes.append(len(X))
            return self

        def risk_score(self, X):
            return np.linspace(0, 1, len(X))

        def params(self):
            return {}

    dev = make_dev(CREDITCARD)
    record = runner.run_cv(Spy, dev=dev, n_bootstrap=0, n_folds=2)

    for size, outcome in zip(sizes, record.folds, strict=True):
        assert size == outcome.n_train
        # n_train_fraud counts the fraud in the fold's training block; under
        # track C none of it was removed.
        assert outcome.n_train_fraud > 0


def test_supervised_model_in_track_c_is_rejected():
    """A supervised model with no labels would train on a constant target and
    still produce a number. Better a hard failure than a plausible one."""

    class Impossible(SentinelModel):
        name = "supervised_but_blind"
        scale_columns = "none"
        handles_missing = True
        supervised = True
        label_regime = UNLABELED

        def fit(self, X, y):
            return self

        def risk_score(self, X):
            return np.zeros(len(X))

        def params(self):
            return {}

    with pytest.raises(LabelRegimeError, match="generates_own_labels"):
        runner.run_cv(Impossible, dev=make_dev(CREDITCARD), n_bootstrap=0, n_folds=2)


def test_a_label_generating_model_may_run_in_track_c():
    """The exception the guard exists for: a PU cascade manufactures its own
    labels, so it is supervised and blind at the same time."""

    class Cascade(SentinelModel):
        name = "cascade"
        scale_columns = "none"
        handles_missing = True
        supervised = True
        generates_own_labels = True
        label_regime = UNLABELED

        def fit(self, X, y):
            assert int(np.asarray(y).sum()) == 0, "still handed no real labels"
            return self

        def risk_score(self, X):
            return np.linspace(0, 1, len(X))

        def params(self):
            return {}

    record = runner.run_cv(Cascade, dev=make_dev(CREDITCARD), n_bootstrap=0, n_folds=2)
    assert len(record.folds) == 2


# --------------------------------------------------------------------------
# Registry wiring
# --------------------------------------------------------------------------


def test_every_registered_model_declares_a_track():
    """Every entry, on whichever dataset it can run — the entity-only half of
    the registry needs this check as much as the rest."""
    for name in MODEL_REGISTRY:
        spec = CREDITCARD if name in models_for(CREDITCARD) else IEEECIS
        model = get_model(name, spec)
        assert model.track in {"A", "B", "C"}, f"{name} has track {model.track!r}"


def test_the_roster_covers_all_three_tracks():
    tracks = models_by_track(CREDITCARD)
    assert set(tracks) == {"A", "B", "C"}
    assert tracks["C"] == ["ae_contaminated", "if_contaminated", "pu_cascade"]


def test_only_the_cascade_is_supervised_without_labels():
    """Track C holds two kinds of model, and conflating them would lose the
    distinction the track exists to draw. The contaminated twins ignore `y`
    entirely; the cascade *is* supervised and manufactures the target it needs.
    `generates_own_labels` is the single exemption to the runner's rule that a
    supervised model cannot run label-blind, so exactly one model may carry it.
    """
    exempt = [
        name
        for name in models_by_track(CREDITCARD)["C"]
        if get_model(name, CREDITCARD).generates_own_labels
    ]
    assert exempt == ["pu_cascade"]

    for name in ("if_contaminated", "ae_contaminated"):
        assert get_model(name, CREDITCARD).supervised is False


def test_contaminated_variants_differ_from_their_one_class_twins():
    """Same estimator, same hyperparameters — only the label budget differs.
    That is what makes B minus C a measurement of the budget itself."""
    one_class = get_model("isolation_forest", CREDITCARD)
    blind = get_model("if_contaminated", CREDITCARD)

    assert one_class.track == "B"
    assert blind.track == "C"
    assert type(one_class) is type(blind)
    assert one_class.params() == blind.params()


def test_trains_on_normal_only_now_reflects_the_regime():
    assert get_model("isolation_forest", CREDITCARD).trains_on_normal_only is True
    assert get_model("if_contaminated", CREDITCARD).trains_on_normal_only is False
    assert get_model("xgboost", CREDITCARD).trains_on_normal_only is False


def test_regime_reaches_the_experiment_record():
    dev = make_dev(CREDITCARD)
    record = runner.run_cv(
        lambda: get_model("if_contaminated", CREDITCARD), dev=dev, n_bootstrap=0, n_folds=2
    )

    regime = record.model["label_regime"]
    assert regime["track"] == "C"
    assert regime["sees_labels"] is False
    assert record.model["track"] == "C"


# --------------------------------------------------------------------------
# Partial labels — the lag model
# --------------------------------------------------------------------------


def test_partial_label_reveals_the_requested_share(labelled):
    X, y = labelled
    _, revealed = PartialLabel(reveal_fraction=1 / 3, seed=0).apply(X, y)

    assert revealed.sum() == 1  # 3 positives, one third revealed
    assert len(revealed) == len(y)


@pytest.mark.parametrize("fraction", [0.0, 1.0])
def test_partial_label_endpoints_match_the_pure_tracks(labelled, fraction):
    X, y = labelled
    _, revealed = PartialLabel(reveal_fraction=fraction, seed=0).apply(X, y)

    expected = 0 if fraction == 0.0 else int(y.sum())
    assert revealed.sum() == expected


def test_partial_label_is_reproducible(labelled):
    X, y = labelled
    first = PartialLabel(0.5, seed=7).apply(X, y)[1]
    second = PartialLabel(0.5, seed=7).apply(X, y)[1]

    pd.testing.assert_series_equal(first, second)


def test_partial_label_rejects_an_impossible_fraction():
    with pytest.raises(LabelRegimeError, match="reveal_fraction"):
        PartialLabel(reveal_fraction=1.5)


def test_shared_instances_are_the_documented_ones():
    assert FULLY_SUPERVISED.track == "A"
    assert ONE_CLASS.track == "B"
    assert UNLABELED.track == "C"
