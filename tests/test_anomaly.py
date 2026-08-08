"""Anomaly and hybrid model tests.

The properties tested here are the ones the runner and the protocol depend on,
not model quality. The important ones are the leakage guarantees inside the
hybrid, where the nesting — anomaly components fitted inside the outer `fit` —
is the only thing standing between the design and a validation-set leak.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.datasets import CREDITCARD
from src.evaluation import runner
from src.models import get_model
from src.models.anomaly import IsolationForestAnomaly
from src.models.hybrid import AnomalyAugmentedModel
from tests.conftest import make_dev

FEATURE_COLUMNS = [c for c in CREDITCARD.expected_columns if c != CREDITCARD.target_column]
BEHAVIOURAL_COLUMNS = [c for c in FEATURE_COLUMNS if c != CREDITCARD.time_column]

ANOMALY_MODELS = ["isolation_forest", "autoencoder"]
HYBRID_MODELS = ["xgboost_hybrid", "xgboost_hybrid_iforest"]


# --------------------------------------------------------------------------
# Anomaly models
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ANOMALY_MODELS)
def test_anomaly_models_declare_themselves_unsupervised(name):
    model = get_model(name)

    assert model.supervised is False
    assert model.trains_on_normal_only is True


@pytest.mark.parametrize("name", ANOMALY_MODELS)
def test_anomaly_models_exclude_the_split_coordinate(name):
    """Time is a split coordinate, not a behavioural feature.

    Under an expanding window every validation timestamp lies beyond every
    training one, so a model that scores on Time penalises later rows for being
    later — noise with respect to fraud.
    """
    model = get_model(name)

    selected = model.select_features(FEATURE_COLUMNS, CREDITCARD)
    assert CREDITCARD.time_column not in selected
    assert selected == BEHAVIOURAL_COLUMNS
    assert len(selected) == 29


@pytest.mark.parametrize("name", ANOMALY_MODELS)
def test_anomaly_models_never_see_fraud_during_fit(name):
    dev = make_dev()
    record = runner.run_cv(lambda: get_model(name), dev=dev, n_bootstrap=0, n_folds=2)

    assert record.model["trains_on_normal_only"] is True
    for outcome in record.folds:
        # The runner strips fraud before fitting, so n_train is the normal count.
        assert outcome.n_train < outcome.n_train + outcome.n_train_fraud


@pytest.mark.parametrize("name", ANOMALY_MODELS)
def test_anomaly_models_rank_the_planted_signal(name):
    """Not a quality bar — only that the score points the right way."""
    dev = make_dev()
    record = runner.run_cv(lambda: get_model(name), dev=dev, n_bootstrap=0, n_folds=2)

    for outcome in record.folds:
        fraud = outcome.val_scores[outcome.val_y == 1]
        normal = outcome.val_scores[outcome.val_y == 0]
        assert fraud.mean() > normal.mean(), f"{name} ranks fraud below normal"


def test_isolation_forest_score_direction():
    """sklearn's score_samples is higher-is-normal; risk_score must invert it."""
    dev = make_dev()
    train = dev.iloc[:2_000]
    normal = train[train[CREDITCARD.target_column] == 0]

    model = IsolationForestAnomaly()
    columns = model.select_features(FEATURE_COLUMNS, CREDITCARD)
    model.fit(normal[columns], normal[CREDITCARD.target_column])

    scores = model.risk_score(dev.iloc[2_000:][columns])
    raw = model._model.score_samples(dev.iloc[2_000:][columns])
    assert np.allclose(scores, -raw)


def test_autoencoder_reconstruction_error_is_non_negative():
    dev = make_dev()
    record = runner.run_cv(lambda: get_model("autoencoder"), dev=dev, n_bootstrap=0, n_folds=2)

    for outcome in record.folds:
        assert (outcome.val_scores >= 0).all(), "MSE cannot be negative"


def test_autoencoder_scales_every_input_by_default():
    """Reconstruction error sums over features, so spread must be comparable."""
    model = get_model("autoencoder")
    selected = model.select_features(FEATURE_COLUMNS, CREDITCARD)
    assert model.resolve_scale_columns(selected, CREDITCARD) == BEHAVIOURAL_COLUMNS

    minimal = get_model("autoencoder_minimal_scale")
    minimal_selected = minimal.select_features(FEATURE_COLUMNS, CREDITCARD)
    assert minimal.resolve_scale_columns(minimal_selected, CREDITCARD) == [
        CREDITCARD.amount_column
    ]
    assert minimal_selected == selected


# --------------------------------------------------------------------------
# Feature budget
# --------------------------------------------------------------------------


def test_runner_subsets_to_the_declared_features():
    dev = make_dev()
    seen: list[list[str]] = []

    class Narrow(IsolationForestAnomaly):
        """Declares a three-column budget; the runner must hand it exactly that."""

        def select_features(self, available, spec):
            return ["V1", "V2", "V3"]

        def fit(self, X, y):
            seen.append(list(X.columns))
            return super().fit(X, y)

    record = runner.run_cv(
        lambda: Narrow(name="narrow"), dev=dev, n_bootstrap=0, n_folds=2
    )

    assert seen and all(columns == ["V1", "V2", "V3"] for columns in seen)
    assert record.n_features == 3
    assert record.model["n_features"] == 3


def test_unknown_declared_scale_column_is_rejected():
    """A scale declaration naming a column outside the feature space is a bug,
    not something to silently ignore."""

    class Bad(IsolationForestAnomaly):
        scale_columns = ["V1", "not_a_column"]

    with pytest.raises(ValueError, match="not present in the feature space"):
        Bad().resolve_scale_columns(FEATURE_COLUMNS, CREDITCARD)


def test_default_feature_budget_is_the_full_contract():
    model = get_model("xgboost")
    assert model.select_features(FEATURE_COLUMNS, CREDITCARD) == FEATURE_COLUMNS
    assert model.describe(FEATURE_COLUMNS, CREDITCARD)["n_features"] == 30


# --------------------------------------------------------------------------
# Hybrid — leakage is the whole point
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", HYBRID_MODELS)
def test_hybrid_runs_and_reports_the_augmented_budget(name):
    dev = make_dev()
    record = runner.run_cv(lambda: get_model(name), dev=dev, n_bootstrap=0, n_folds=2)

    declaration = record.model
    n_added = len(declaration["params"]["added_features"])
    assert declaration["n_features_after_augmentation"] == declaration["n_features"] + n_added
    assert n_added == (2 if name == "xgboost_hybrid" else 1)


def test_hybrid_anomaly_components_fit_only_on_training_normals():
    """The nesting is the leakage guarantee; this checks it holds."""
    dev = make_dev()
    fitted_on: list[int] = []

    class SpyComponent(IsolationForestAnomaly):
        def fit(self, X, y):
            fitted_on.append(len(X))
            assert set(np.unique(y).tolist()) == {0}, "component saw fraud"
            return super().fit(X, y)

    hybrid = AnomalyAugmentedModel(
        anomaly_factories={"iforest": SpyComponent}, name="spy_hybrid"
    ).bind(CREDITCARD)
    train = dev.iloc[:2_000]
    X, y = train[FEATURE_COLUMNS], train[CREDITCARD.target_column]

    hybrid.fit(X, y)
    assert fitted_on == [int((y == 0).sum())]


def test_hybrid_does_not_refit_components_when_scoring():
    dev = make_dev()
    calls: list[int] = []

    class CountingComponent(IsolationForestAnomaly):
        def fit(self, X, y):
            calls.append(1)
            return super().fit(X, y)

    hybrid = AnomalyAugmentedModel(
        anomaly_factories={"iforest": CountingComponent}, name="counting_hybrid"
    ).bind(CREDITCARD)
    train, test = dev.iloc[:2_000], dev.iloc[2_000:]

    hybrid.fit(train[FEATURE_COLUMNS], train[CREDITCARD.target_column])
    assert len(calls) == 1

    hybrid.risk_score(test[FEATURE_COLUMNS])
    hybrid.risk_score(test[FEATURE_COLUMNS])
    assert len(calls) == 1, "scoring refitted an anomaly component"


def test_hybrid_augmentation_is_deterministic():
    dev = make_dev()
    train, test = dev.iloc[:2_000], dev.iloc[2_000:]

    hybrid = get_model("xgboost_hybrid_iforest")
    hybrid.fit(train[FEATURE_COLUMNS], train[CREDITCARD.target_column])

    first = hybrid.risk_score(test[FEATURE_COLUMNS])
    second = hybrid.risk_score(test[FEATURE_COLUMNS])
    assert np.array_equal(first, second)


def test_hybrid_rejects_a_training_fold_with_no_normals():
    dev = make_dev(n=200)
    X = dev[FEATURE_COLUMNS]
    y = dev[CREDITCARD.target_column].copy()
    y[:] = 1

    with pytest.raises(ValueError, match="no normal rows"):
        get_model("xgboost_hybrid_iforest").fit(X, y)
