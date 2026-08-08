"""Layer 6 — Model: feature matrix in, risk score out.

One interface, one runner, one experiment record. The alternative — a bespoke
script per model — produces numbers that cannot be compared, because the thing
that differs between two scripts is never only the model.

Four declarations carry the contract:

* `scale_columns` — preprocessing is *per model*, not global. Tree ensembles
  declare `"none"`, which is a positive claim of invariance rather than an
  oversight; linear, distance, and kernel methods declare `"all"`. A
  quantum-vs-classical comparison where the two sides were scaled differently
  is not a comparison.
* `select_features` — which of the available columns this model consumes. Takes
  the actual feature space rather than a frozen list, so the same model works
  on a 30-column dataset and a 400-column one.
* `requires_entity` — whether the model needs per-entity history. Behavioural
  models exclude themselves from datasets that carry no entity information, the
  same way feature groups do.
* `label_regime` — how much label information reaches `fit`. This is what makes
  "supervised" and "unsupervised" precise rather than a habit of speech; see
  `src/models/regime.py`.
* `handles_missing` — whether the estimator reads NaN natively.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
import pandas as pd

from src.datasets import DatasetSpec, get_spec
from src.features import FeatureGroup
from src.models.regime import FULLY_SUPERVISED, ONE_CLASS, LabelRegime

#: Symbolic declarations resolve against the actual feature space at run time,
#: which is what lets one model definition work on datasets whose columns are
#: named differently:
#:
#:   "none"     nothing — a claim of scale invariance (tree ensembles)
#:   "all"      every column the model consumes (linear, distance, kernel)
#:   "default"  the dataset's declared default (creditcard: Time + Amount)
#:   "amount"   the amount column alone
#:
#: An explicit list is still allowed where the columns are genuinely fixed.
ScaleSpec = list[str] | Literal["all", "none", "default", "amount"]


class SentinelModel(ABC):
    """A fitted-then-scored model. Higher `risk_score` means more suspicious."""

    def __init_subclass__(cls, **kwargs) -> None:
        """Reject the declaration that `label_regime` replaced.

        `trains_on_normal_only` used to be a settable flag and is now a view of
        the regime. A subclass still assigning it would shadow the property and
        silently do nothing — the runner reads the regime. Silent no-ops are how
        this project has lost time before, so it fails loudly instead.
        """
        super().__init_subclass__(**kwargs)
        if "trains_on_normal_only" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} sets trains_on_normal_only, which no longer has "
                "any effect. Declare `label_regime = ONE_CLASS` instead "
                "(src/models/regime.py)."
            )

    #: Identifier; becomes the results directory name.
    name: str = "unnamed"

    #: Columns needing rescaling. `"none"` is a claim, not an omission.
    scale_columns: ScaleSpec = "none"

    #: Whether this model needs per-entity history to be meaningful.
    requires_entity: bool = False

    #: Whether the estimator reads NaN natively. Tree ensembles do, and for them
    #: a median fill would destroy information: on IEEE-CIS "this identity field
    #: was never collected" is a signal in its own right. Linear, distance, and
    #: kernel methods raise on NaN and need the runner to impute first.
    handles_missing: bool = False

    #: How much label information reaches `fit`. Declared, never implicit — a
    #: model must say which track it belongs to before it can run.
    label_regime: LabelRegime = FULLY_SUPERVISED

    #: Whether `fit` uses `y` at all. False for pure anomaly detection.
    supervised: bool = True

    #: True only for models that manufacture their own labels (PU cascades).
    #: Without it, a supervised model in track C would train on a constant
    #: target and still produce a number.
    generates_own_labels: bool = False

    #: Set by `bind()`. Most models never read it; wrappers that must resolve a
    #: nested component's feature set at fit time do.
    _spec: DatasetSpec | None = None

    # --- Applicability ----------------------------------------------------

    def applies_to(self, spec: DatasetSpec) -> bool:
        """Whether this model can run on the given dataset at all."""
        return spec.has_entity or not self.requires_entity

    def bind(self, spec: DatasetSpec) -> "SentinelModel":
        """Attach the dataset spec. The runner calls this before `fit`.

        Kept separate from `fit` so the fit signature stays `(X, y)` — the
        shape every sklearn-shaped estimator already has.
        """
        self._spec = spec
        return self

    @property
    def spec(self) -> DatasetSpec:
        if self._spec is None:
            raise RuntimeError(f"{self.name}: bind(spec) was not called before fit()")
        return self._spec

    @property
    def track(self) -> str:
        return self.label_regime.track

    @property
    def trains_on_normal_only(self) -> bool:
        """Kept as a read-only view of the regime for records and reporting."""
        return self.label_regime.filters_to_normal

    # --- Feature and scaling resolution -----------------------------------

    def feature_groups(self) -> "list[FeatureGroup] | None":
        """Layer-4 groups this model needs, or None for the runner's default.

        Declared on the model for the same reason `scale_columns` is: a registry
        name has to identify one complete experiment. `xgboost` and
        `xgboost_behavioral` are the same estimator and differ only in which
        feature groups ran, and if that difference lived in a command-line flag
        instead, `--all` could not reproduce either of them and the record would
        not say which had happened.

        Note that the choice is the model's, but the *fitting* stays layer 4's:
        the runner builds a fresh pipeline per fold and fits it on the training
        rows, so a model cannot reach a feature that saw the evaluation fold.
        """
        return None

    def select_features(self, available: list[str], spec: DatasetSpec) -> list[str]:
        """Columns this model consumes. Default: everything the pipeline made."""
        return list(available)

    def resolve_scale_columns(self, columns: list[str], spec: DatasetSpec) -> list[str]:
        """Turn the `scale_columns` declaration into a concrete column list.

        Anything the model does not consume is dropped from the result: scaling
        a column the model never sees is wasted work at best and a silent
        inconsistency at worst.
        """
        if self.scale_columns == "none":
            return []
        if self.scale_columns == "all":
            return list(columns)
        if self.scale_columns == "default":
            return [c for c in spec.default_scale_columns if c in columns]
        if self.scale_columns == "amount":
            return [spec.amount_column] if spec.amount_column in columns else []

        declared = list(self.scale_columns)
        unknown = [c for c in declared if c not in columns]
        if unknown:
            raise ValueError(
                f"{self.name} declares scale_columns not present in the feature "
                f"space: {unknown}"
            )
        return declared

    # --- Core -------------------------------------------------------------

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SentinelModel":
        """Fit on training data. Must not look at anything outside `X`, `y`."""

    @abstractmethod
    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        """Score rows so larger values rank as more likely fraud.

        The scale is deliberately unconstrained — AUPRC, ROC-AUC and
        precision@k are all rank-based, and forcing anomaly scores into [0, 1]
        would imply a calibration these models do not have.
        """

    @abstractmethod
    def params(self) -> dict:
        """Hyperparameters, JSON-serializable, for the experiment record."""

    # --- Explanation ------------------------------------------------------

    #: Whether this model can attribute its own score to individual features.
    #: A declaration rather than a capability test, for the same reason
    #: `scale_columns` is: layer 10 must be able to ask before it computes.
    explainable: bool = False

    def shap_contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Exact per-feature contributions, shape (n_rows, n_features + 1).

        The trailing column is the bias, so each row sums to the model's margin
        output. Tree ensembles compute this exactly through TreeSHAP, which
        their own libraries already implement — wrapping a separate package
        around the same algorithm would add a dependency and no accuracy.

        Contributions live in *margin* space, not probability. That is what
        makes them additive, and additivity is the entire property an
        attribution is worth reporting for.
        """
        raise NotImplementedError(
            f"{self.name} does not attribute its score. Check `explainable` first."
        )

    # --- Record -----------------------------------------------------------

    def describe(self, available: list[str] | None = None, spec: DatasetSpec | None = None) -> dict:
        """The declaration recorded alongside every result."""
        spec = get_spec(spec)
        columns = self.select_features(list(available), spec) if available else None
        return {
            "name": self.name,
            "class": type(self).__name__,
            "supervised": self.supervised,
            "label_regime": self.label_regime.describe(),
            "track": self.track,
            "trains_on_normal_only": self.trains_on_normal_only,
            "requires_entity": self.requires_entity,
            "handles_missing": self.handles_missing,
            "scale_columns": self.scale_columns
            if isinstance(self.scale_columns, str)
            else list(self.scale_columns),
            "feature_columns": columns,
            "n_features": len(columns) if columns is not None else None,
            "params": self.params(),
        }


class AnomalyModel(SentinelModel):
    """Base for models that learn normality and score deviation from it.

    Drops the time column from the inputs. Under an expanding window *every*
    validation timestamp lies beyond the training range — that is the point of
    the split — so a model that reconstructs or isolates on time penalises rows
    for being later, which is noise with respect to fraud.

    The time column is a split coordinate, not a behavioural feature.
    """

    supervised = False
    label_regime: LabelRegime = ONE_CLASS

    def select_features(self, available: list[str], spec: DatasetSpec) -> list[str]:
        return [c for c in available if c != spec.time_column]


class SklearnModel(SentinelModel):
    """Shared plumbing for estimators exposing `predict_proba`."""

    def __init__(
        self,
        estimator,
        *,
        name: str,
        scale_columns: ScaleSpec = "all",
    ):
        self.name = name
        self.scale_columns = scale_columns
        self._estimator = estimator

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SklearnModel":
        self._estimator.fit(X, y)
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        return self._estimator.predict_proba(X)[:, 1]

    def params(self) -> dict:
        return {
            key: value
            for key, value in self._estimator.get_params().items()
            if isinstance(value, (int, float, str, bool, type(None)))
        }
