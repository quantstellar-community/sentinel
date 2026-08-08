"""Supervised baselines.

All three handle the 578:1 imbalance through loss weighting rather than
resampling. That is deliberate for Phase 1: SMOTE and its variants add a
synthesis step whose own hyperparameters would then need to be searched, and
`docs/research_synthesis.md` lists "SMOTE before the split" as a leakage trap.
Weighting changes no data and cannot leak. Resampling can be revisited later,
measured against these results with `metrics.compare_auprc`.

None of the three uses early stopping. Carving a validation slice out of each
training fold to stop on would shrink folds that already hold few fraud cases,
and would introduce a second, undocumented split. Fixed iteration counts are
recorded in the experiment instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src import config
from src.models.base import ScaleSpec, SentinelModel, SklearnModel


def _positive_weight(y: pd.Series) -> float:
    """n_negative / n_positive on the training fold — about 578 here."""
    n_positive = int(np.asarray(y).sum())
    n_negative = int(len(y) - n_positive)
    if n_positive == 0:
        raise ValueError("training fold contains no fraud cases")
    return n_negative / n_positive


class LogisticRegressionBaseline(SklearnModel):
    """The Phase 0 reference point.

    Defaults reproduce the recorded Phase 0 baseline exactly: only `Time` and
    `Amount` are rescaled. `scale_columns` is a constructor argument so the
    registry can also expose a fully-scaled variant — with a linear model the
    scaling choice is a real modelling decision, and the registry answers it
    with a measurement rather than an assertion.
    """

    def __init__(
        self,
        scale_columns: ScaleSpec = "default",
        name: str = "logreg",
        **overrides,
    ):
        # `overrides` exists so the tuning layer can search `C` and
        # `class_weight`. With none supplied the estimator is byte-for-byte the
        # Phase 0 baseline, which is what keeps `verify_migration` at 12/12.
        settings = {
            "class_weight": "balanced",
            "max_iter": 2_000,
            "random_state": config.SEED,
            **overrides,
        }
        super().__init__(
            LogisticRegression(**settings),
            name=name,
            scale_columns=scale_columns,
        )


class XGBoostBaseline(SentinelModel):
    """Gradient boosting, tuned for ranking rather than accuracy.

    `eval_metric="aucpr"` matches the primary metric; `scale_pos_weight` is set
    from the training fold, so it adapts as the expanding window grows.
    """

    name = "xgboost"
    scale_columns: ScaleSpec = "none"  # trees are invariant to monotone rescaling
    handles_missing = True   # XGBoost learns a default direction per split
    explainable = True       # TreeSHAP, exact, from the booster

    def __init__(self, *, balanced: bool = True, name: str | None = None, **overrides):
        from xgboost import XGBClassifier  # local: keeps src.models importable without it

        self.balanced = balanced
        if name:
            self.name = name
        self._settings = {
            "n_estimators": 400,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "eval_metric": "aucpr",
            "tree_method": "hist",
            "random_state": config.SEED,
            "n_jobs": -1,
            **overrides,
        }
        self._cls = XGBClassifier
        self._model = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "XGBoostBaseline":
        weight = {"scale_pos_weight": _positive_weight(y)} if self.balanced else {}
        self._model = self._cls(**weight, **self._settings)
        self._model.fit(X, y)
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("fit() before risk_score()")
        return self._model.predict_proba(X)[:, 1]

    def shap_contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Exact TreeSHAP from the booster itself — no extra dependency.

        `pred_contribs` is the same algorithm the standalone `shap` package
        calls for tree ensembles, implemented inside XGBoost. The result is in
        margin space and sums to `predict(output_margin=True)` per row.
        """
        import xgboost as xgb

        if self._model is None:
            raise RuntimeError("fit() before shap_contributions()")
        return self._model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)

    def params(self) -> dict:
        return {"balanced": self.balanced, **self._settings}


class LightGBMBaseline(SentinelModel):
    """LightGBM with the same weighting strategy, for a second boosting opinion.

    `min_child_samples` is raised well above the default: leaves holding a
    handful of rows are meaningless when the entire positive class is a few
    hundred cases, and unconstrained leaves are how boosting memorises them.

    `reg_lambda` is set explicitly and is not optional. LightGBM defaults it to
    0 where XGBoost defaults it to 1, and with `scale_pos_weight` near 578 an
    unpenalised leaf value grows until the logistic output saturates: measured
    on fold 0, the unregularised model produced 65 distinct scores across 45,397
    rows, with 2,062 rows tied at exactly 1.0 of which only 45 were fraud.
    ROC-AUC still read 0.80 — ranking within a tie block is arbitrary but the
    blocks themselves are ordered — while AUPRC collapsed to 0.0148, barely
    above the 0.0017 floor. Setting it to 1.0 restored 43,024 distinct scores
    and AUPRC 0.7604.

    Matching XGBoost's default also keeps the two boosting models comparable:
    they should differ in implementation, not in how hard they are penalised.

    Open question, deliberately not settled here: dropping the weighting
    entirely scored higher still on that one fold (AUPRC 0.8181). Adopting it on
    the strength of a single fold would be the selection error this protocol
    exists to prevent — it needs a run across all folds and a paired test.
    """

    name = "lightgbm"
    scale_columns: ScaleSpec = "none"
    handles_missing = True
    explainable = True

    def __init__(self, *, balanced: bool = True, name: str | None = None, **overrides):
        from lightgbm import LGBMClassifier

        self.balanced = balanced
        if name:
            self.name = name
        self._settings = {
            "n_estimators": 400,
            "num_leaves": 31,
            "max_depth": -1,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "subsample_freq": 1,
            "colsample_bytree": 0.8,
            "min_child_samples": 50,
            "reg_lambda": 1.0,
            "random_state": config.SEED,
            "n_jobs": -1,
            "verbose": -1,
            **overrides,
        }
        self._cls = LGBMClassifier
        self._model = None

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LightGBMBaseline":
        weight = {"scale_pos_weight": _positive_weight(y)} if self.balanced else {}
        self._model = self._cls(**weight, **self._settings)
        self._model.fit(X, y)
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("fit() before risk_score()")
        return self._model.predict_proba(X)[:, 1]

    def shap_contributions(self, X: pd.DataFrame) -> np.ndarray:
        """Exact TreeSHAP from LightGBM's own booster, margin space, bias last."""
        if self._model is None:
            raise RuntimeError("fit() before shap_contributions()")
        return np.asarray(self._model.predict(X, pred_contrib=True), dtype="float64")

    def params(self) -> dict:
        return {"balanced": self.balanced, **self._settings}
