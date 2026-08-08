"""Tests for the track-C cascade.

Two things have to hold, and the first is the reason the class exists at all:
the model is supervised yet must never see a label. The runner's regime gate
gives it a constant target, and the model checks that for itself — a cascade
that quietly received real labels would report track C while being track A, and
every B-minus-C number in the project would be wrong.

The second is that the bootstrap does what it says. Its thresholds are declared
prior knowledge, not discoveries, so the tests pin the arithmetic: the flagged
head is exactly the declared fraction, and the ambiguous middle is dropped
rather than called negative.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import IEEECIS
from src.evaluation import runner
from src.models import get_model
from src.models.base import SentinelModel
from src.models.pu import PUCascade, PUCascadeError
from tests.conftest import make_dev


class SpySupervised(SentinelModel):
    """Records the label vector the cascade hands its supervised stage."""

    name = "spy_supervised"
    scale_columns = "none"
    handles_missing = True
    calls: list[dict] = []

    def fit(self, X, y):
        SpySupervised.calls.append(
            {"n_rows": len(X), "n_positive": int(np.asarray(y).sum())}
        )
        return self

    def risk_score(self, X):
        return X["V1"].to_numpy(dtype=float)

    def params(self):
        return {}


@pytest.fixture(autouse=True)
def clear_spy():
    SpySupervised.calls = []
    yield
    SpySupervised.calls = []


def cascade(**overrides) -> PUCascade:
    return PUCascade(supervised_factory=SpySupervised, **overrides)


# --------------------------------------------------------------------------
# It must stay label-blind
# --------------------------------------------------------------------------


def test_the_cascade_never_receives_a_positive_label():
    """The whole roster's B-minus-C axis depends on this. A cascade fed real
    labels would report track C while being track A."""
    seen: list[int] = []

    class Watching(PUCascade):
        name = "watching"

        def fit(self, X, y):
            seen.append(int(np.asarray(y).sum()))
            return super().fit(X, y)

    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    record = runner.run_cv(Watching, spec=IEEECIS, dev=dev, n_bootstrap=0, n_folds=2)

    assert seen == [0, 0], f"the cascade was shown positives: {seen}"
    assert all(outcome.val_y.sum() > 0 for outcome in record.folds), (
        "the evaluation folds must contain fraud, or this test proves nothing"
    )


def test_a_real_label_vector_reaching_fit_is_rejected():
    dev = make_dev(IEEECIS, n=600)
    X = dev.drop(columns=[IEEECIS.target_column])

    with pytest.raises(PUCascadeError, match="declares the unlabeled regime"):
        cascade().bind(IEEECIS).fit(X, dev[IEEECIS.target_column])


def test_the_runner_accepts_it_only_because_it_makes_its_own_labels():
    """`generates_own_labels` is the single exemption to the rule that a
    supervised model cannot run in track C."""
    model = get_model("pu_cascade", IEEECIS)

    assert model.supervised is True
    assert model.label_regime.sees_labels is False
    assert model.generates_own_labels is True


# --------------------------------------------------------------------------
# The bootstrap arithmetic
# --------------------------------------------------------------------------


def test_the_flagged_head_is_the_declared_fraction():
    """The alert rate is an input assumption, not a discovery — history.md §32
    records a design where that circularity went unnoticed. Pinning it here
    keeps it visible."""
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    X = dev.drop(columns=[IEEECIS.target_column])
    model = cascade(assumed_positive_rate=0.10).bind(IEEECIS)

    model.fit(X, pd.Series(0, index=X.index))

    flagged = int(model.pseudo_labels.sum())
    assert abs(flagged / len(X) - 0.10) < 0.01


def test_the_ambiguous_middle_is_discarded_rather_than_called_negative():
    """Rows just below the threshold are where undiscovered fraud sits. Calling
    them legitimate would teach the supervised stage that the detector's
    near-misses are safe."""
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    X = dev.drop(columns=[IEEECIS.target_column])
    model = cascade(
        assumed_positive_rate=0.05, reliable_negative_fraction=0.50
    ).bind(IEEECIS)

    model.fit(X, pd.Series(0, index=X.index))

    trained_on = SpySupervised.calls[-1]["n_rows"]
    assert abs(trained_on / len(X) - 0.55) < 0.02, (
        "the supervised stage should see the head plus the tail, and nothing between"
    )
    assert trained_on < len(X), "the discarded band is what makes this a cascade"


def test_the_supervised_stage_gets_both_classes():
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    X = dev.drop(columns=[IEEECIS.target_column])
    cascade().bind(IEEECIS).fit(X, pd.Series(0, index=X.index))

    call = SpySupervised.calls[-1]
    assert 0 < call["n_positive"] < call["n_rows"], "a constant target teaches nothing"


def test_degenerate_anomaly_scores_raise_rather_than_train_on_a_constant():
    class Flat(SentinelModel):
        name = "flat"
        scale_columns = "none"
        handles_missing = True
        supervised = False

        def fit(self, X, y):
            return self

        def risk_score(self, X):
            return np.zeros(len(X))

        def params(self):
            return {}

    dev = make_dev(IEEECIS, n=400)
    X = dev.drop(columns=[IEEECIS.target_column])
    model = PUCascade(
        anomaly_factory=Flat, supervised_factory=SpySupervised
    ).bind(IEEECIS)

    with pytest.raises(PUCascadeError, match="degenerate"):
        model.fit(X, pd.Series(0, index=X.index))


# --------------------------------------------------------------------------
# Declarations
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "positive_rate, negative_fraction",
    [(0.6, 0.5), (0.0, 0.5), (1.0, 0.5), (0.05, 0.0), (0.05, 1.0)],
)
def test_incoherent_thresholds_are_rejected_at_construction(
    positive_rate, negative_fraction
):
    with pytest.raises(PUCascadeError):
        PUCascade(
            assumed_positive_rate=positive_rate,
            reliable_negative_fraction=negative_fraction,
        )


def test_the_record_states_the_prior_it_assumed():
    """The alert rate is the one number a reader has to see to judge the result,
    so it belongs in the record rather than in a default nobody reads."""
    params = get_model("pu_cascade", IEEECIS).params()

    assert params["assumed_positive_rate"] == 0.05
    assert params["discarded_band"] == 0.45
    assert params["anomaly"] == "isolation_forest"
