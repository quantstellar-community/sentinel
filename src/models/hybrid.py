"""Supervised model with unsupervised anomaly scores as extra features.

This is the combination step the README asks for when it says *anomaly is not
fraud*: the anomaly layer produces a signal, and a separate decision layer
weighs that signal against supervised evidence. The pattern follows Carcillo et
al. 2019, "Combining Unsupervised and Supervised Learning in Credit Card Fraud
Detection".

Leakage safety comes from the nesting rather than from a check. The anomaly
components are fitted inside `fit`, which by construction only ever receives a
training fold; `risk_score` reuses those fitted components without refitting.
No anomaly component observes a validation row before it is scored.

What this measures, and what it does not: on a benchmark whose fraud comes from
the same distribution the supervised model trained on, the anomaly components
see exactly the features the supervised model already has, so there is little
reason to expect a gain. A null result here is informative but narrow — it says
nothing about novel fraud, which is what the layer is for. See
`scripts/novel_fraud_experiment.py`.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.data.preprocessor import Preprocessor
from src.models.anomaly import AutoencoderAnomaly, IsolationForestAnomaly
from src.models.base import ScaleSpec, SentinelModel
from src.models.supervised import XGBoostBaseline


class AnomalyAugmentedModel(SentinelModel):
    """Wraps a supervised model, appending one column per anomaly component.

    Each component keeps its own declared preprocessing: the wrapper fits a
    private `Preprocessor` per component on the training fold. Handing every
    component one globally-scaled frame would quietly override the per-model
    scaling contract that `base.SentinelModel` sets up.
    """

    scale_columns: ScaleSpec = "none"  # the outer model is a tree ensemble
    handles_missing = True             # ...which also reads NaN natively

    def __init__(
        self,
        supervised_factory: Callable[[], SentinelModel] | None = None,
        anomaly_factories: dict[str, Callable[[], SentinelModel]] | None = None,
        *,
        name: str = "xgboost_hybrid",
    ):
        self.name = name
        self._supervised_factory = supervised_factory or XGBoostBaseline
        self._anomaly_factories = anomaly_factories or {
            "iforest": IsolationForestAnomaly,
            "autoencoder": AutoencoderAnomaly,
        }
        self._supervised: SentinelModel | None = None
        self._anomalies: dict[str, tuple[SentinelModel, Preprocessor | None, list[str]]] = {}

    @property
    def anomaly_feature_names(self) -> list[str]:
        return [f"anomaly__{key}" for key in self._anomaly_factories]

    def _augment(self, X: pd.DataFrame) -> pd.DataFrame:
        """Append one anomaly score column per fitted component."""
        augmented = X.copy()
        for key, (model, preprocessor, columns) in self._anomalies.items():
            frame = preprocessor.transform(X) if preprocessor is not None else X
            augmented[f"anomaly__{key}"] = model.risk_score(frame[columns])
        return augmented

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "AnomalyAugmentedModel":
        normal = np.asarray(y) == 0
        if not normal.any():
            raise ValueError("no normal rows to fit the anomaly components on")

        spec = self.spec
        available = list(X.columns)

        self._anomalies = {}
        for key, factory in self._anomaly_factories.items():
            component = factory().bind(spec)
            columns = component.select_features(available, spec)
            scale_columns = component.resolve_scale_columns(columns, spec)

            preprocessor = None
            if scale_columns or not component.handles_missing:
                # Fitted on the normal rows of the training fold only — the same
                # data the component itself is about to be trained on.
                preprocessor = Preprocessor(
                    columns=scale_columns, impute=not component.handles_missing
                ).fit(X[normal])

            frame = preprocessor.transform(X) if preprocessor is not None else X
            component.fit(frame.loc[normal, columns], y[normal])
            self._anomalies[key] = (component, preprocessor, columns)

        self._supervised = self._supervised_factory().bind(spec)
        self._supervised.fit(self._augment(X), y)
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._supervised is None:
            raise RuntimeError("fit() before risk_score()")
        return self._supervised.risk_score(self._augment(X))

    def params(self) -> dict:
        return {
            "supervised": self._supervised_factory().name,
            "anomaly_components": {
                key: factory().name for key, factory in self._anomaly_factories.items()
            },
            "added_features": self.anomaly_feature_names,
        }

    def describe(self, available=None, spec=None) -> dict:
        """Report the *augmented* feature budget, not only the input one.

        The wrapper consumes 30 columns and hands its supervised model 32. A
        comparison against plain XGBoost is therefore not equal-budget, and the
        record has to say so rather than quietly reporting 30.
        """
        declaration = super().describe(available, spec)
        if declaration["n_features"] is None:
            return declaration
        declaration["n_features_after_augmentation"] = declaration["n_features"] + len(
            self._anomaly_factories
        )
        return declaration


def iforest_only_hybrid() -> AnomalyAugmentedModel:
    """XGBoost plus the Isolation Forest score alone.

    Separates the two components' contributions: if the full hybrid moves and
    this one does not, the autoencoder carries the effect, and vice versa.
    """
    return AnomalyAugmentedModel(
        anomaly_factories={"iforest": IsolationForestAnomaly},
        name="xgboost_hybrid_iforest",
    )


__all__ = ["AnomalyAugmentedModel", "iforest_only_hybrid"]
