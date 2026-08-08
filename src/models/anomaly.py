"""Unsupervised anomaly models — the "learn the normal world first" layer.

All of these fit on the normal class alone and never see a fraud label. Expect
them to score far below the supervised baselines on AUPRC: they solve a harder
problem with less information, on a benchmark built from exactly the fraud the
supervised models trained on. That gap is the expected result, not a failure,
and `scripts/novel_fraud_experiment.py` exists because a same-distribution
AUPRC benchmark cannot measure what this layer is actually for.

**Why the time column is excluded.** Every model here inherits from
`AnomalyModel`, which drops it, and this is not cosmetic. Under an expanding
window every validation timestamp lies strictly beyond every training
timestamp — that is the point of the split. A model that reconstructs or
isolates on time therefore assigns a systematic penalty to validation rows that
grows the further into the fold they sit, which is noise with respect to fraud.
The time column is a split coordinate, not a behavioural feature.

The tree ensembles in `supervised.py` keep it because they were already
measured with it and a tree can ignore an uninformative split; the registry
carries `isolation_forest_with_time` so this choice is checked, not asserted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src import config
from src.datasets import DatasetSpec
from src.models.base import AnomalyModel, ScaleSpec
from src.models.regime import LabelRegime


class IsolationForestAnomaly(AnomalyModel):
    """Isolation Forest over the behavioural features.

    The anomaly score is `-score_samples`, so larger means more suspicious in
    line with the `risk_score` contract. `contamination` is left at its default
    because it only shifts the offset used by `predict`, and every metric in
    this project is rank-based — setting it would change no result while
    implying a calibration the model does not have.
    """

    scale_columns: ScaleSpec = "none"  # trees are invariant to monotone rescaling

    def __init__(
        self,
        *,
        name: str = "isolation_forest",
        keep_time: bool = False,
        label_regime: LabelRegime | None = None,
        **overrides,
    ):
        self.name = name
        self.keep_time = keep_time
        if label_regime is not None:
            self.label_regime = label_regime
        self._settings = {
            "n_estimators": 300,
            "max_samples": "auto",
            "random_state": config.SEED,
            "n_jobs": -1,
            **overrides,
        }
        self._model: IsolationForest | None = None

    def select_features(self, available: list[str], spec: DatasetSpec) -> list[str]:
        if self.keep_time:
            return list(available)
        return super().select_features(available, spec)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "IsolationForestAnomaly":
        self._model = IsolationForest(**self._settings)
        self._model.fit(X)  # y unused: the runner has already removed fraud
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("fit() before risk_score()")
        return -self._model.score_samples(X)

    def params(self) -> dict:
        return {"keep_time": self.keep_time, **self._settings}


class AutoencoderAnomaly(AnomalyModel):
    """Dense autoencoder; the anomaly score is per-row reconstruction error.

    Architecture follows `docs/research_synthesis.md` §3.3 — 30→20→14→7→14→20→30
    minus the excluded time column. The 7-unit bottleneck is deliberate: it is
    the classical counterpart of the qubit compression a Quantum Autoencoder
    performs in Phase 2, where reconstruction error maps to (1 − fidelity).
    Keeping the shapes aligned now is what makes that comparison meaningful.

    Scaling matters here in a way it did not for the linear and tree models.
    Reconstruction error is a sum over features, so a feature with wider spread
    contributes more error regardless of how informative it is. The registry
    carries a minimally-scaled variant so the choice is measured rather than
    assumed — the treatment `logreg_full_scale` gave the same question for
    linear models.
    """

    scale_columns: ScaleSpec = "all"

    def __init__(
        self,
        *,
        name: str = "autoencoder",
        scale_columns: ScaleSpec | None = None,
        label_regime: LabelRegime | None = None,
        hidden: tuple[int, ...] = (20, 14),
        bottleneck: int = 7,
        epochs: int = 30,
        batch_size: int = 512,
        learning_rate: float = 1e-3,
    ):
        self.name = name
        if scale_columns is not None:
            self.scale_columns = scale_columns
        if label_regime is not None:
            self.label_regime = label_regime
        self.hidden = tuple(hidden)
        self.bottleneck = bottleneck
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate

        self._model = None
        self._torch = None

    def _build(self, n_features: int):
        from torch import nn

        sizes = [n_features, *self.hidden, self.bottleneck]

        encoder: list[nn.Module] = []
        for a, b in zip(sizes[:-1], sizes[1:], strict=True):
            encoder += [nn.Linear(a, b), nn.ReLU()]

        decoder: list[nn.Module] = []
        reversed_sizes = sizes[::-1]
        for a, b in zip(reversed_sizes[:-1], reversed_sizes[1:], strict=True):
            decoder += [nn.Linear(a, b), nn.ReLU()]
        decoder = decoder[:-1]  # linear output: reconstructions may be negative

        return nn.Sequential(*encoder, *decoder)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "AutoencoderAnomaly":
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        torch.manual_seed(config.SEED)
        self._torch = torch

        data = torch.tensor(X.to_numpy(dtype="float32"))
        loader = DataLoader(
            TensorDataset(data),
            batch_size=self.batch_size,
            shuffle=True,
            generator=torch.Generator().manual_seed(config.SEED),
        )

        model = self._build(data.shape[1])
        optimizer = torch.optim.Adam(model.parameters(), lr=self.learning_rate)
        criterion = torch.nn.MSELoss()

        model.train()
        for _ in range(self.epochs):
            for (batch,) in loader:
                optimizer.zero_grad()
                loss = criterion(model(batch), batch)
                loss.backward()
                optimizer.step()

        model.eval()
        self._model = model
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("fit() before risk_score()")

        torch = self._torch
        data = torch.tensor(X.to_numpy(dtype="float32"))
        with torch.no_grad():
            error = ((self._model(data) - data) ** 2).mean(dim=1)
        return error.numpy().astype(float)

    def params(self) -> dict:
        return {
            "hidden": list(self.hidden),
            "bottleneck": self.bottleneck,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
        }
