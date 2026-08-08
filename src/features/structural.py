"""Structural feature groups — make data model-ready without adding signal.

These are the groups safe to enable by default: `PassThrough` is the identity
on numeric columns, and `CategoricalEncode` converts strings a model cannot
consume into codes it can. Neither creates information that was not already
there, so turning them on does not move any result that was previously
obtainable.

`TimeOfDay` sits here too but is deliberately **not** in the default pipeline —
it derives new columns, which changes the feature space and therefore every
downstream number. It is opt-in and belongs to a measured comparison.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.datasets import DatasetSpec
from src.features.base import FeatureGroup, NotFittedError

#: Codes reserved outside the fitted range so a model can tell the two apart.
#: "Absent" and "never seen in training" are different signals, and collapsing
#: them would discard the distinction for no benefit.
MISSING_CODE = -1
UNSEEN_CODE = -2


class PassThrough(FeatureGroup):
    """Every numeric column except the target and the join key.

    The join key is excluded because a row identifier carries no signal but
    correlates with time, which makes it an excellent way to leak the split
    ordering into a tree.
    """

    name = "passthrough"
    derived = False

    def __init__(self, exclude: list[str] | None = None):
        self.exclude = list(exclude or [])
        self._columns: list[str] | None = None

    def fit(self, train: pd.DataFrame, spec: DatasetSpec) -> "PassThrough":
        dropped = {spec.target_column, *self.exclude}
        if spec.join_key:
            dropped.add(spec.join_key)

        self._columns = [
            c
            for c in train.columns
            if c not in dropped and pd.api.types.is_numeric_dtype(train[c])
        ]
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[self.output_columns()]

    def output_columns(self) -> list[str]:
        if self._columns is None:
            raise NotFittedError(f"{self.name}: fit() first")
        return list(self._columns)


class CategoricalEncode(FeatureGroup):
    """Integer codes for columns a model cannot consume as strings.

    Encodes every non-numeric column found at fit time, plus anything the spec
    declares as categorical (which catches numeric-looking columns that are
    really labels). The vocabulary is learned on the training fold: a value
    absent from training maps to `UNSEEN_CODE` rather than extending the
    mapping, because fitting the encoder on the full frame would tell the model
    which categories are going to appear in the future.
    """

    name = "categorical_encode"
    derived = False

    def __init__(self):
        self._mapping: dict[str, dict[object, int]] = {}
        self._columns: list[str] | None = None

    def fit(self, train: pd.DataFrame, spec: DatasetSpec) -> "CategoricalEncode":
        dropped = {spec.target_column}
        if spec.join_key:
            dropped.add(spec.join_key)

        detected = [
            c
            for c in train.columns
            if c not in dropped and not pd.api.types.is_numeric_dtype(train[c])
        ]
        declared = [c for c in spec.categorical_columns if c in train.columns]

        # Preserve the frame's own column order so the output is deterministic.
        wanted = set(detected) | set(declared)
        self._columns = [c for c in train.columns if c in wanted and c not in dropped]

        self._mapping = {}
        for column in self._columns:
            values = train[column].dropna().unique()
            self._mapping[column] = {value: code for code, value in enumerate(sorted(values, key=str))}
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = self.output_columns()
        if not columns:
            return pd.DataFrame(index=df.index)

        encoded = {}
        for column in columns:
            mapping = self._mapping[column]
            series = df[column]
            codes = series.map(mapping)
            codes = codes.where(~series.isna(), MISSING_CODE)
            codes = codes.fillna(UNSEEN_CODE)
            encoded[column] = codes.astype("int32")

        return pd.DataFrame(encoded, index=df.index)

    def output_columns(self) -> list[str]:
        if self._columns is None:
            raise NotFittedError(f"{self.name}: fit() first")
        return list(self._columns)

    def describe(self) -> dict:
        base = super().describe()
        base["vocabulary_sizes"] = {c: len(m) for c, m in self._mapping.items()}
        return base


class TimeOfDay(FeatureGroup):
    """Hour-of-day and day-of-week derived from the time column.

    **Not enabled by default.** It creates columns, so switching it on changes
    every downstream number and has to be justified by a paired comparison.

    On creditcard the EDA already argues against it: the busiest hours are not
    the most fraudulent ones (volume peaks at hour 21, fraud at hour 11), so
    the cycle it encodes is not the cycle fraud follows. On a dataset spanning
    182 days rather than 48 hours the question is worth reopening.
    """

    name = "time_of_day"
    derived = True

    def __init__(self):
        self._time_column: str | None = None

    def fit(self, train: pd.DataFrame, spec: DatasetSpec) -> "TimeOfDay":
        self._time_column = spec.time_column
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._time_column is None:
            raise NotFittedError(f"{self.name}: fit() first")

        seconds = df[self._time_column].to_numpy(dtype="float64")
        return pd.DataFrame(
            {
                "HOUR_OF_DAY": np.floor((seconds % 86_400) / 3_600),
                "DAY_OF_WEEK": np.floor(seconds / 86_400) % 7,
            },
            index=df.index,
        )

    def output_columns(self) -> list[str]:
        if self._time_column is None:
            raise NotFittedError(f"{self.name}: fit() first")
        return ["HOUR_OF_DAY", "DAY_OF_WEEK"]
