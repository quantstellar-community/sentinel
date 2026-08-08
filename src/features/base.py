"""Layer 4 — Feature Pipeline: composable groups, each declaring its own scope.

A group is a small, independent transformation that knows two things about
itself: whether it can run on a given dataset at all, and what columns it
produces. The pipeline composes them and drops the ones that do not apply.

That `applies_to()` check is what lets a *single* group list serve every
dataset. Groups needing per-entity history exclude themselves when the spec
declares no entity, so there is no per-dataset configuration and no branching
on dataset name.

Groups fall into two kinds, and the distinction matters:

* **Structural** groups make data model-ready without adding information —
  passing numeric columns through, turning strings into codes. They are safe to
  enable by default because they change no result that was not already blocked.
* **Derived** groups create new signal — rolling windows, velocity ratios,
  time-of-day. Enabling one changes the feature space, and therefore every
  downstream number. They stay opt-in and are measured against a baseline
  rather than assumed to help.

The invariant every group shares with the scaler: `fit` sees the training fold
alone, `transform` learns nothing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from src.datasets import DatasetSpec, get_spec


class FeatureError(ValueError):
    """Raised when a pipeline is used inconsistently."""


class NotFittedError(RuntimeError):
    """Raised when `transform` is called before `fit`."""


class FeatureGroup(ABC):
    """One composable block of the feature matrix."""

    name: str = "unnamed"

    #: Whether this group needs per-entity history to mean anything.
    requires_entity: bool = False

    #: False for groups that only reshape existing columns; True for groups
    #: that create new signal and therefore change every downstream result.
    derived: bool = True

    def applies_to(self, spec: DatasetSpec) -> bool:
        return spec.has_entity or not self.requires_entity

    @abstractmethod
    def fit(self, train: pd.DataFrame, spec: DatasetSpec) -> "FeatureGroup":
        """Learn any statistics from the training fold alone."""

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return this group's columns for `df`. Learns nothing."""

    @abstractmethod
    def output_columns(self) -> list[str]:
        """Columns this group produces. Valid only after `fit`."""

    def narrowed_to(self, entities) -> "FeatureGroup":
        """A copy that keeps only the state needed for the given entities.

        Layer 10 re-runs the pipeline once per candidate value, and a group
        holding a whole training fold of history would rebuild all of it to
        learn about one row. Groups with no per-entity state — every structural
        one — have nothing to narrow and return themselves.

        Not an approximation: an entity's features depend on that entity's rows
        and nothing else, which the layer-4 tests establish separately.
        """
        return self

    def describe(self) -> dict:
        return {
            "name": self.name,
            "class": type(self).__name__,
            "requires_entity": self.requires_entity,
            "derived": self.derived,
            "n_output_columns": len(self.output_columns()),
        }


class FeaturePipeline:
    """Composes feature groups into one matrix.

    Groups that do not apply to the spec are dropped at construction, so the
    caller passes the same list for every dataset and the pipeline works out
    what is possible.
    """

    def __init__(self, groups: list[FeatureGroup], spec: DatasetSpec | str | None = None):
        self.spec = get_spec(spec)
        self.groups = [g for g in groups if g.applies_to(self.spec)]
        self.skipped = [g.name for g in groups if not g.applies_to(self.spec)]
        self._fitted = False

    def fit(self, train: pd.DataFrame) -> "FeaturePipeline":
        for group in self.groups:
            group.fit(train, self.spec)

        seen: dict[str, str] = {}
        for group in self.groups:
            for column in group.output_columns():
                if column in seen:
                    raise FeatureError(
                        f"column {column!r} produced by both {seen[column]!r} "
                        f"and {group.name!r}"
                    )
                seen[column] = group.name

        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise NotFittedError("call fit() on the training fold before transform()")

        parts = [group.transform(df) for group in self.groups]
        if not parts:
            raise FeatureError("pipeline produced no columns")

        out = pd.concat(parts, axis=1)
        return out[self.output_columns()]

    def fit_transform(self, train: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train).transform(train)

    def output_columns(self) -> list[str]:
        return [c for group in self.groups for c in group.output_columns()]

    def narrowed_to(self, entities) -> "FeaturePipeline":
        """A fitted copy carrying only the history the given entities need.

        The original is left intact, so the caller cannot accidentally shrink
        the pipeline an experiment is still using.
        """
        if not self._fitted:
            raise NotFittedError("narrow a fitted pipeline, not an empty one")

        narrowed = FeaturePipeline([], self.spec)
        narrowed.groups = [group.narrowed_to(entities) for group in self.groups]
        narrowed.skipped = list(self.skipped)
        narrowed._fitted = True
        return narrowed

    def describe(self) -> dict:
        return {
            "groups": [group.describe() for group in self.groups],
            "skipped": self.skipped,
            "n_columns": len(self.output_columns()) if self._fitted else None,
        }
