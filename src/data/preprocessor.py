"""Leakage-safe imputation and scaling.

Both transformations learn their statistics from the training fold and from
nothing else. Fitting either on the full frame leaks the evaluation
distribution into training — the third of the leakage traps in
`docs/research_synthesis.md`, and the one that leaves no trace in the output.

Both are *per-model* decisions rather than global defaults:

* Tree ensembles are invariant to monotone rescaling and read NaN natively, so
  they declare neither. Imputing for them would actively destroy information —
  on IEEE-CIS "this identity field was never collected" is a signal, and a
  median fill erases it.
* Linear, distance, and kernel methods need both. `LogisticRegression` and
  `IsolationForest` raise on NaN; reconstruction error is a sum over features,
  so an unscaled wide-range column dominates it regardless of relevance.
"""

from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import RobustScaler

from src.datasets import DatasetSpec, get_spec


class NotFittedError(RuntimeError):
    """Raised when `transform` is called before `fit`."""


class Preprocessor:
    """Median imputation then RobustScaler, over declared columns.

    RobustScaler (median / IQR) rather than StandardScaler because these
    datasets have heavy tails — creditcard's `Amount` has skew 16.98 and
    several V columns exceed kurtosis 200. A mean/std scaler would be dominated
    by exactly the outliers those numbers describe.

    Imputation runs first so the scaler's quantiles are computed on the same
    values the model will see.
    """

    def __init__(
        self,
        columns: list[str] | None = None,
        spec: DatasetSpec | str | None = None,
        *,
        impute: bool = False,
    ) -> None:
        if columns is None:
            columns = get_spec(spec).default_scale_columns
        self.columns = list(columns)
        self.impute = impute

        self._scaler = RobustScaler()
        self._medians: pd.Series | None = None
        self._fitted = False
        self._fit_n_rows: int | None = None

    def fit(self, train: pd.DataFrame) -> "Preprocessor":
        """Learn medians and IQR from the training split only."""
        missing = [c for c in self.columns if c not in train.columns]
        if missing:
            raise KeyError(f"columns not present in training frame: {missing}")

        frame = train
        if self.impute:
            # Every column, not just the scaled ones: a model that cannot read
            # NaN cannot read it anywhere.
            self._medians = train.median(numeric_only=True)
            # A column that is entirely NaN in training has no median; zero is
            # the only defensible fill, and the column carries no signal anyway.
            self._medians = self._medians.fillna(0.0)
            frame = self._apply_impute(train)

        # An empty column list is a legitimate declaration — "this model is
        # scale-invariant" — so it fits as a no-op rather than raising.
        if self.columns:
            self._scaler.fit(frame[self.columns])

        self._fitted = True
        self._fit_n_rows = len(train)
        return self

    def _apply_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._medians is None:
            return df
        out = df.copy()
        shared = [c for c in out.columns if c in self._medians.index]
        out[shared] = out[shared].fillna(self._medians[shared])
        return out

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the training-set statistics. Never re-fits."""
        if not self._fitted:
            raise NotFittedError("call fit() on the training split before transform()")

        out = self._apply_impute(df) if self.impute else df.copy()
        if self.columns:
            out[self.columns] = self._scaler.transform(out[self.columns])
        return out

    def fit_transform(self, train: pd.DataFrame) -> pd.DataFrame:
        """Convenience for the training split. Do not call this on test data."""
        return self.fit(train).transform(train)

    @property
    def fitted_on_n_rows(self) -> int | None:
        """Row count of the frame this was fitted on — checked by the tests."""
        return self._fit_n_rows
