"""Model-interface conformance and runner-level leakage tests.

Runs on synthetic data, so no dataset is required. Model quality is not tested
here — that is what the experiment records are for. What is tested is that every
registered model honours the contract the runner and the comparison machinery
depend on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.preprocessor import Preprocessor
from src.datasets import CREDITCARD, IEEECIS, DatasetSpec
from src.datasets import spec as spec_module
from src.evaluation import runner
from src.features import behavioral_pipeline
from src.models import MODEL_REGISTRY, get_model, models_for
from src.models.base import SentinelModel
from src.models.regime import ONE_CLASS
from src.models.tuning import TunedModel
from tests.conftest import make_dev

FEATURE_COLUMNS = [c for c in CREDITCARD.expected_columns if c != CREDITCARD.target_column]
PCA_COLUMNS = [f"V{i}" for i in range(1, 29)]




ALL_MODELS = sorted(MODEL_REGISTRY)


def spec_for(name: str) -> DatasetSpec:
    """The dataset a registered model can actually run on.

    Behavioural models require entity information that creditcard does not
    carry, so a registry-wide test has to ask each model where it belongs rather
    than assume the default. Restricting these tests to creditcard instead would
    be the wrong fix: it would leave the entity-only half of the registry
    without any conformance coverage at all.
    """
    return CREDITCARD if name in models_for(CREDITCARD) else IEEECIS


def dev_for(name: str, spec: DatasetSpec) -> pd.DataFrame:
    """A synthetic development set the model under test can actually run on.

    The tuning wrapper holds a quarter of each training fold back to rank
    candidates on, and refuses to search when that slice is too thin — the
    default fixture leaves it 13 positives. A conformance test checks the
    model's interface, not its behaviour at a realistic prevalence, so the frame
    is enriched rather than the guard weakened.
    """
    if isinstance(MODEL_REGISTRY[name](), TunedModel):
        return make_dev(spec, n=6_000, n_unique_times=3_000, fraud_rate=0.15)
    return make_dev(spec)


def feature_space(spec: DatasetSpec) -> list[str]:
    """The columns a model would be offered on `spec`, built the way the runner
    builds them — through whatever pipeline applies, not from a frozen list."""
    dev = make_dev(spec, n=400, n_unique_times=200)
    return behavioral_pipeline(spec).fit(dev).output_columns()


# --------------------------------------------------------------------------
# Registry and interface conformance
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ALL_MODELS)
def test_registry_builds_a_conforming_model(name):
    spec = spec_for(name)
    model = get_model(name, spec)
    available = feature_space(spec)

    assert isinstance(model, SentinelModel)
    assert model.name, "every model needs a name — it becomes the results directory"
    resolved = model.resolve_scale_columns(model.select_features(available, spec), spec)
    assert set(resolved) <= set(available)


@pytest.mark.parametrize("name", ALL_MODELS)
def test_declaration_is_json_serializable(name):
    """The declaration goes into every experiment record."""
    import json

    spec = spec_for(name)
    json.dumps(get_model(name, spec).describe(feature_space(spec), spec))


@pytest.mark.parametrize("name", ALL_MODELS)
def test_factory_returns_a_fresh_instance_each_call(name):
    """The runner builds one model per fold; shared state would leak the
    previous fold's training data into the next."""
    spec = spec_for(name)
    assert get_model(name, spec) is not get_model(name, spec)


def test_unknown_model_name_lists_the_options():
    with pytest.raises(KeyError, match="unknown model"):
        get_model("does_not_exist")


@pytest.mark.parametrize("name", ALL_MODELS)
def test_risk_score_ranks_and_has_the_right_shape(name):
    """Honours the model's declared contract, exactly as the runner does.

    Handing a model the full 30 columns when it declared 29 is not a harmless
    shortcut: giving the autoencoder `Time` made reconstruction error climb
    monotonically through the validation fold and swamp the fraud signal
    entirely. A test that bypasses `select_features()` measures the wrong thing.
    """
    spec = spec_for(name)
    dev = dev_for(name, spec)
    cut = int(len(dev) * 0.66)
    train, test = dev.iloc[:cut], dev.iloc[cut:]

    model = get_model(name, spec)
    pipeline = runner.pipeline_for(model, spec).fit(train)
    X_train, X_test = pipeline.transform(train), pipeline.transform(test)

    columns = model.select_features(list(X_train.columns), spec)
    X_train, X_test = X_train[columns], X_test[columns]

    scale_columns = model.resolve_scale_columns(columns, spec)
    if scale_columns or not model.handles_missing:
        pre = Preprocessor(
            columns=scale_columns, impute=not model.handles_missing
        ).fit(X_train)
        X_train, X_test = pre.transform(X_train), pre.transform(X_test)

    X_fit, y_fit = model.label_regime.apply(X_train, train[spec.target_column])
    model.fit(X_fit, y_fit)
    scores = model.risk_score(X_test)

    assert scores.shape == (len(X_test),)
    assert np.isfinite(scores).all()

    # Higher must mean more suspicious. The fixture plants signal in both the
    # raw columns and the entity histories, so this holds whichever of the two a
    # model consumes.
    y = test[spec.target_column].to_numpy()
    assert scores[y == 1].mean() > scores[y == 0].mean()


def test_tree_models_declare_scale_invariance():
    """Not an oversight — a positive claim the runner relies on to skip scaling."""
    for name in ("xgboost", "lightgbm"):
        model = get_model(name)
        assert model.scale_columns == "none"
        assert model.resolve_scale_columns(FEATURE_COLUMNS, CREDITCARD) == []


def test_the_two_logreg_variants_differ_only_in_scaling():
    minimal = get_model("logreg")
    full = get_model("logreg_full_scale")

    assert minimal.resolve_scale_columns(FEATURE_COLUMNS, CREDITCARD) == (
        CREDITCARD.default_scale_columns
    )
    assert full.resolve_scale_columns(FEATURE_COLUMNS, CREDITCARD) == FEATURE_COLUMNS
    assert minimal.params() == full.params()


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


def test_run_cv_covers_every_fold_and_keeps_scores():
    dev = make_dev()
    record = runner.run_cv(lambda: get_model("logreg"), dev=dev, n_bootstrap=0, n_folds=3)

    assert len(record.folds) == 3
    for outcome in record.folds:
        assert outcome.val_scores.shape == outcome.val_y.shape
        assert outcome.val_y.sum() > 0
        assert outcome.fit_seconds >= 0


def test_run_cv_never_trains_on_the_validation_block():
    """The guarantee the whole protocol rests on, checked at runner level.

    A spy model records the timestamps it was fitted on and the timestamps it
    was asked to score; every training row must strictly precede every scored
    row within the same fold.
    """
    dev = make_dev()
    fits: list[tuple[float, float]] = []
    scores: list[tuple[float, float]] = []

    class Spy(SentinelModel):
        name = "spy"
        scale_columns = "none"

        def fit(self, X, y):
            fits.append((X[CREDITCARD.time_column].min(), X[CREDITCARD.time_column].max()))
            return self

        def risk_score(self, X):
            scores.append((X[CREDITCARD.time_column].min(), X[CREDITCARD.time_column].max()))
            return np.linspace(0, 1, len(X))

        def params(self):
            return {}

    runner.run_cv(Spy, dev=dev, n_bootstrap=0, n_folds=3)

    assert len(fits) == len(scores) == 3
    for (train_min, train_max), (val_min, val_max) in zip(fits, scores, strict=True):
        assert train_max < val_min, "a training row is contemporaneous with a scored row"
        assert train_min <= train_max < val_min <= val_max

    # The window expands: each fold trains on strictly more history.
    train_ends = [train_max for _, train_max in fits]
    assert train_ends == sorted(train_ends)
    assert len(set(train_ends)) == len(train_ends)


def test_runner_honours_trains_on_normal_only():
    """Anomaly models must never see fraud during fitting."""
    dev = make_dev()
    seen_labels: list[set[int]] = []

    class NormalOnly(SentinelModel):
        name = "normal_only"
        scale_columns = "none"
        label_regime = ONE_CLASS
        supervised = False

        def fit(self, X, y):
            seen_labels.append(set(np.unique(y).tolist()))
            return self

        def risk_score(self, X):
            return np.asarray(X[CREDITCARD.amount_column], dtype=float)

        def params(self):
            return {}

    runner.run_cv(NormalOnly, dev=dev, n_bootstrap=0, n_folds=2)

    assert seen_labels, "fit was never called"
    for labels in seen_labels:
        assert labels == {0}, f"anomaly model saw fraud during fit: {labels}"


def test_saturated_scores_are_flagged():
    """Regression guard for a real failure.

    LightGBM without an L2 penalty produced 65 distinct scores across 45,397
    rows; AUPRC collapsed to the random floor while ROC-AUC still read 0.80, so
    the metrics table alone did not reveal it.
    """
    dev = make_dev()

    class Saturated(SentinelModel):
        name = "saturated"
        scale_columns = "none"

        def fit(self, X, y):
            return self

        def risk_score(self, X):
            # Near-binary output, exactly the failure shape observed.
            return (np.asarray(X[PCA_COLUMNS[0]]) > 0.5).astype(float)

        def params(self):
            return {}

    record = runner.run_cv(Saturated, dev=dev, n_bootstrap=0, n_folds=2)

    for outcome in record.folds:
        assert outcome.resolution_warning is not None
        assert "distinct scores" in outcome.resolution_warning
        assert "tie at the maximum" in outcome.resolution_warning


def test_healthy_scores_are_not_flagged():
    dev = make_dev()
    record = runner.run_cv(lambda: get_model("logreg"), dev=dev, n_bootstrap=0, n_folds=2)

    for outcome in record.folds:
        assert outcome.resolution_warning is None
        assert outcome.n_distinct_scores > 0.5 * outcome.val_scores.size


@pytest.mark.parametrize("name", ALL_MODELS)
def test_registered_models_produce_usable_score_resolution(name):
    """Every model in the registry must rank, not bucket."""
    spec = spec_for(name)
    dev = dev_for(name, spec)
    record = runner.run_cv(
        lambda: get_model(name, spec), spec=spec, dev=dev, n_bootstrap=0, n_folds=2
    )

    for outcome in record.folds:
        assert outcome.resolution_warning is None, (
            f"{name} fold {outcome.fold}: {outcome.resolution_warning}"
        )


def test_runner_rejects_non_finite_scores():
    dev = make_dev()

    class Nan(SentinelModel):
        name = "nan"
        scale_columns = "none"

        def fit(self, X, y):
            return self

        def risk_score(self, X):
            out = np.zeros(len(X))
            out[0] = np.nan
            return out

        def params(self):
            return {}

    with pytest.raises(runner.ExperimentError, match="NaN"):
        runner.run_cv(Nan, dev=dev, n_bootstrap=0, n_folds=2)


def test_runner_rejects_a_badly_shaped_score():
    dev = make_dev()

    class Broken(SentinelModel):
        name = "broken"
        scale_columns = "none"

        def fit(self, X, y):
            return self

        def risk_score(self, X):
            return np.zeros(len(X) + 1)

        def params(self):
            return {}

    with pytest.raises(runner.ExperimentError, match="expected"):
        runner.run_cv(Broken, dev=dev, n_bootstrap=0, n_folds=2)


def test_record_serializes_and_reports_aggregates():
    import json

    dev = make_dev()
    record = runner.run_cv(lambda: get_model("logreg"), dev=dev, n_bootstrap=0, n_folds=3)
    payload = record.to_dict()

    json.dumps(payload)
    assert payload["fold_auprcs"] == record.fold_auprcs
    assert payload["n_features"] == len(FEATURE_COLUMNS)
    assert record.mean_auprc == pytest.approx(np.mean(record.fold_auprcs))


def test_saved_scores_round_trip(tmp_path, monkeypatch):
    """Comparison depends on reading these back byte-for-byte."""
    monkeypatch.setattr(spec_module, "EXPERIMENTS_ROOT", tmp_path)

    dev = make_dev()
    record = runner.run_cv(lambda: get_model("logreg"), dev=dev, n_bootstrap=0, n_folds=3)
    runner.save(record)

    restored = runner.load_scores(record.name)
    assert sorted(restored) == [0, 1, 2]
    for outcome in record.folds:
        scores, y = restored[outcome.fold]
        assert np.array_equal(scores, outcome.val_scores)
        assert np.array_equal(y, outcome.val_y)


def test_missing_results_point_at_the_command(tmp_path, monkeypatch):
    monkeypatch.setattr(spec_module, "EXPERIMENTS_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError, match="run_experiment.py"):
        runner.load_scores("never_run")
