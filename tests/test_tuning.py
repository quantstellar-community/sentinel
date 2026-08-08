"""Tests for the hyperparameter search layer.

The property that matters is the same one every other layer here is built
around, and it is invisible in a metrics table: the search must not be able to
see the rows it will later be scored on. A search that peeked would produce a
better number on every fold and leave no trace, so the tests are built around
what a peeking implementation could not satisfy.

The second concern is subtler. The inner split is taken by *position*, which is
only a temporal split because the training fold arrives in time order. That
assumption is load-bearing — get it wrong and the search trains on the future of
its own validation slice — so it is asserted rather than trusted.
"""

from __future__ import annotations

import pytest

from src.datasets import CREDITCARD, IEEECIS
from src.evaluation import runner
from src.models import MODEL_REGISTRY, get_model, models_for
from src.models.base import SentinelModel
from src.models.supervised import XGBoostBaseline
from src.models.tuning import (
    INERT_IN_SEARCH,
    LIGHTGBM_SPACE,
    LOGREG_SPACE,
    XGBOOST_SPACE,
    TunedModel,
    TuningError,
)
from tests.conftest import make_dev

TINY_SPACE = {"max_depth": [2, 3], "n_estimators": [10, 20]}


class Recorder(SentinelModel):
    """A stand-in estimator that records what it was fitted on.

    Scores by a single column so the search has something to rank, and keeps the
    row count and the last timestamp of every fit in a class-level log.
    """

    name = "recorder"
    scale_columns = "none"
    handles_missing = True
    fits: list[dict] = []

    def __init__(self, **params):
        self.params_seen = params

    def fit(self, X, y):
        Recorder.fits.append(
            {
                "n_rows": len(X),
                "max_time": float(X[IEEECIS.time_column].max()),
                "params": dict(self.params_seen),
            }
        )
        self._weight = 1.0 + len(self.params_seen)
        return self

    def risk_score(self, X):
        # Deterministic but params-dependent, so candidates differ in score.
        return (X["V1"].to_numpy() * self._weight) % 1.0

    def params(self):
        return dict(self.params_seen)


@pytest.fixture(autouse=True)
def clear_recorder():
    Recorder.fits = []
    yield
    Recorder.fits = []


def tuned_recorder(**overrides) -> TunedModel:
    settings = {
        "name": "tuned_recorder",
        "n_candidates": 4,
        "min_inner_positives": 1,
        **overrides,
    }
    return TunedModel(Recorder, TINY_SPACE, **settings)


# --------------------------------------------------------------------------
# The leakage property
# --------------------------------------------------------------------------


def test_the_search_never_sees_a_row_from_the_evaluation_fold():
    """The nesting guarantee, checked rather than argued.

    Every fit the search performs must lie entirely before the validation
    block's first timestamp — including the final refit.
    """
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    runner.run_cv(tuned_recorder, spec=IEEECIS, dev=dev, n_bootstrap=0, n_folds=2)

    folds = runner.splitter.expanding_window_folds(dev, IEEECIS, n_folds=2)
    boundaries = [
        float(dev.iloc[fold.val_idx][IEEECIS.time_column].min()) for fold in folds
    ]

    assert Recorder.fits, "the search never ran"
    # 4 candidates + 1 refit per fold.
    per_fold = len(Recorder.fits) // len(folds)
    for index, boundary in enumerate(boundaries):
        for fit in Recorder.fits[index * per_fold : (index + 1) * per_fold]:
            assert fit["max_time"] < boundary, (
                f"fold {index}: a fit reached time {fit['max_time']}, at or past "
                f"the validation block starting at {boundary}"
            )


def test_candidates_are_scored_on_held_back_rows_not_the_ones_they_fitted():
    """Selecting on the rows a candidate trained on would rank memorisation."""
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    model = tuned_recorder(inner_fraction=0.25).bind(IEEECIS)

    X = dev.drop(columns=[IEEECIS.target_column])
    model.fit(X, dev[IEEECIS.target_column])

    search_fits = [f["n_rows"] for f in Recorder.fits[:-1]]
    refit = Recorder.fits[-1]["n_rows"]

    assert all(n == int(len(X) * 0.75) for n in search_fits), (
        "candidates must be fitted on the inner training slice alone"
    )
    assert refit == len(X), "the winner must be refitted on the whole training fold"


def test_a_shuffled_training_fold_is_rejected_rather_than_split_by_position():
    """If the frame is not in time order, a positional split is not a temporal
    one and the search would train on the future of its own slice."""
    dev = make_dev(IEEECIS, n=600)
    shuffled = dev.sample(frac=1.0, random_state=0)
    model = tuned_recorder().bind(IEEECIS)

    with pytest.raises(TuningError, match="not increasing"):
        model.fit(
            shuffled.drop(columns=[IEEECIS.target_column]),
            shuffled[IEEECIS.target_column],
        )


# --------------------------------------------------------------------------
# Refusing to search on evidence that cannot support one
# --------------------------------------------------------------------------


def test_too_few_positives_raises_instead_of_selecting_on_noise():
    dev = make_dev(IEEECIS, n=400, fraud_rate=0.01)
    model = TunedModel(
        Recorder, TINY_SPACE, name="strict", n_candidates=2, min_inner_positives=500
    ).bind(IEEECIS)

    with pytest.raises(TuningError, match="below the 500"):
        model.fit(dev.drop(columns=[IEEECIS.target_column]), dev[IEEECIS.target_column])


def test_wrapping_an_anomaly_model_is_refused_at_construction():
    """Track B filters positives out of `fit` and track C zeroes them, so the
    AUPRC objective has nothing to rank. Refusing where the wrapper is built
    names the real problem; letting it through would surface later as an
    unhelpful "0 positives" message from a guard about sample size."""
    from src.models.anomaly import IsolationForestAnomaly

    with pytest.raises(TuningError, match="no positive reaches"):
        TunedModel(IsolationForestAnomaly, TINY_SPACE, name="doomed")


def test_tuned_models_decline_creditcard_and_accept_ieeecis():
    """creditcard carries 47-89 positives per fold, so a quarter of the first
    fold's training block is about 20 — a search scored on 20 positives selects
    noise and then reports it as a tuned model."""
    model = MODEL_REGISTRY["xgboost_tuned"]()

    assert model.smallest_inner_positives(CREDITCARD) < 50
    assert model.smallest_inner_positives(IEEECIS) > 500

    assert "xgboost_tuned" not in models_for(CREDITCARD)
    assert "xgboost_tuned" in models_for(IEEECIS)


# --------------------------------------------------------------------------
# The wrapper must not change the contract it is measured against
# --------------------------------------------------------------------------


def test_declarations_are_delegated_rather_than_restated():
    """`xgboost` against `xgboost_tuned` is only a comparison if hyperparameters
    are the one thing that differs. Restating scaling or the label regime on the
    wrapper is how that quietly stops being true."""
    tuned = get_model("xgboost_tuned", IEEECIS)
    plain = XGBoostBaseline()

    assert tuned.scale_columns == plain.scale_columns
    assert tuned.handles_missing == plain.handles_missing
    assert tuned.label_regime is plain.label_regime
    assert tuned.supervised == plain.supervised
    assert tuned.feature_groups() == plain.feature_groups()

    columns = ["Time", "V1", "V2"]
    assert tuned.select_features(columns, IEEECIS) == plain.select_features(
        columns, IEEECIS
    )


def test_a_search_space_cannot_contain_a_parameter_the_runner_reads_first():
    """Regression guard for a real, silent bug.

    `scale_columns` is resolved by layer 7 *before* `fit` runs, so a candidate
    declaring it receives a matrix already built under the outer model's value
    and its own is never consulted. `LOGREG_SPACE` briefly carried it: the
    search trace then showed identical inner scores in pairs differing only in
    that key, and eight draws explored five distinct configurations.

    Nothing raised. The dimension looked like it doubled the coverage while
    actually halving the budget — which is why this fails loudly now.
    """
    with pytest.raises(TuningError, match="never consulted"):
        TunedModel(
            XGBoostBaseline,
            {"max_depth": [3, 5], "scale_columns": ["all", "none"]},
            name="inert",
        )


@pytest.mark.parametrize("key", sorted(INERT_IN_SEARCH))
def test_every_known_inert_parameter_is_rejected(key):
    with pytest.raises(TuningError):
        TunedModel(XGBoostBaseline, {key: [1, 2]}, name="inert")


def test_a_tuned_model_can_reach_the_best_configuration_already_known():
    """The point of tuning is to do at least as well as what is already on the
    shelf, so the incumbent has to be inside the space the search can reach.

    `logreg_tuned` failed this twice. `scale_columns` in the space was inert
    (the runner reads it first), and removing it left the wrapper inheriting
    `"default"` from the prototype — the setting measured as the *worse* of the
    two. Either way the search could not express `logreg_full_scale`, and lost
    to it for a reason unrelated to the parameters it was searching.
    """
    tuned = get_model("logreg_tuned", IEEECIS)

    assert tuned.scale_columns == "all", (
        "logreg_full_scale beats logreg by scaling everything; a tuned variant "
        "locked at 'default' starts from the weaker of the two"
    )
    incumbent = {"C": 1.0, "class_weight": "balanced"}
    assert any(
        all(candidate[k] == v for k, v in incumbent.items())
        for candidate in tuned._candidates()
    ), "the search cannot reach the configuration it has to beat"


def test_the_shipped_spaces_contain_nothing_inert():
    for space in (XGBOOST_SPACE, LIGHTGBM_SPACE, LOGREG_SPACE):
        assert not set(space) & set(INERT_IN_SEARCH)


def test_the_candidate_sample_is_fixed_by_the_seed():
    """Layer 8 pairs two runs on identical rows. If the search drew different
    candidates each time, a comparison would be measuring two searches rather
    than two fits of one model."""
    first = MODEL_REGISTRY["xgboost_tuned"]()._candidates()
    second = MODEL_REGISTRY["xgboost_tuned"]()._candidates()

    assert first == second
    assert len(first) == 16
    assert len({tuple(sorted(c.items())) for c in first}) == len(first), (
        "duplicate candidates waste a fit without testing anything new"
    )


def test_the_search_covers_the_flag_already_known_to_matter():
    """`balanced` moved AUPRC 10% on IEEE-CIS and in the opposite direction on
    creditcard. Fixing it would assume away the only hyperparameter already
    proven to be dataset-dependent."""
    for name in ("xgboost_tuned", "lightgbm_tuned"):
        space = MODEL_REGISTRY[name]()._space
        assert set(space["balanced"]) == {True, False}


def test_the_record_reports_what_won_and_what_was_close():
    dev = make_dev(IEEECIS, n=2_000, n_unique_times=1_000)
    model = tuned_recorder().bind(IEEECIS)
    model.fit(dev.drop(columns=[IEEECIS.target_column]), dev[IEEECIS.target_column])

    params = model.params()
    assert params["wraps"] == "recorder"
    assert params["chosen"] is not None
    assert "inner_auprc" in params["chosen"]
    assert params["search_trace"], "a near-tie must not be reportable as decisive"
    scores = [entry["inner_auprc"] for entry in params["search_trace"]]
    assert scores == sorted(scores, reverse=True)


def test_declaration_is_json_serializable():
    import json

    model = get_model("xgboost_tuned", IEEECIS)
    json.dumps(model.describe(["Time", "V1"], IEEECIS))
