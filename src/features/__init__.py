"""Layer 4 — Feature Pipeline."""

from __future__ import annotations

from src.datasets import DatasetSpec, get_spec
from src.features.base import (
    FeatureError,
    FeatureGroup,
    FeaturePipeline,
    NotFittedError,
)
from src.features.behavioral import (
    BENFORD_MIN_HISTORY,
    EPSILON,
    NO_PRIOR_DAYS,
    RATIO_PAIRS,
    WINDOWS,
    BenfordDeviation,
    EntityFeatureGroup,
    EntityHistory,
    RollingWindows,
    VelocityRatios,
    leading_digit,
)
from src.features.structural import (
    MISSING_CODE,
    UNSEEN_CODE,
    CategoricalEncode,
    PassThrough,
    TimeOfDay,
)


def structural_groups() -> list[FeatureGroup]:
    """Groups that make data model-ready without adding signal.

    This is the default. `PassThrough` is the identity on numeric columns and
    `CategoricalEncode` is a no-op on a dataset with no string columns, so
    enabling them cannot move a result that was already obtainable — which is
    what keeps the creditcard numbers reproducible after this layer landed.
    """
    return [PassThrough(), CategoricalEncode()]


def behavioral_groups() -> list[FeatureGroup]:
    """Groups that encode an entity's own history into each row.

    Every one declares `requires_entity`, so this list is safe to pass on any
    dataset: on one with no entity information the pipeline drops all four and
    the result is the structural pipeline again.

    `TimeOfDay` is deliberately absent even though it is also derived and also
    needs no entity. Adding it here would confound experiment #2 — the
    comparison of raw columns against behavioural ones — with a separate
    question about the daily cycle. It stays independently opt-in so each can be
    measured on its own.
    """
    return [RollingWindows(), VelocityRatios(), EntityHistory(), BenfordDeviation()]


def behavioral_column_names() -> list[str]:
    """Every column the behavioural groups produce, without needing a fit.

    Lets a model declare "behavioural columns only" against a feature space it
    has not seen yet. Derived from the groups themselves rather than written out
    again, so a new window or ratio cannot fall out of the list.
    """
    return [
        column
        for group in behavioral_groups()
        if isinstance(group, EntityFeatureGroup)
        for column in group.column_names()
    ]


def default_pipeline(spec: DatasetSpec | str | None = None) -> FeaturePipeline:
    """The pipeline every experiment uses unless it says otherwise."""
    return FeaturePipeline(structural_groups(), get_spec(spec))


def behavioral_pipeline(spec: DatasetSpec | str | None = None) -> FeaturePipeline:
    """Structural columns plus per-entity behavioural ones."""
    return FeaturePipeline(structural_groups() + behavioral_groups(), get_spec(spec))


__all__ = [
    "BENFORD_MIN_HISTORY",
    "EPSILON",
    "MISSING_CODE",
    "NO_PRIOR_DAYS",
    "RATIO_PAIRS",
    "UNSEEN_CODE",
    "WINDOWS",
    "BenfordDeviation",
    "CategoricalEncode",
    "EntityFeatureGroup",
    "EntityHistory",
    "FeatureError",
    "FeatureGroup",
    "FeaturePipeline",
    "NotFittedError",
    "PassThrough",
    "RollingWindows",
    "TimeOfDay",
    "VelocityRatios",
    "behavioral_column_names",
    "behavioral_groups",
    "behavioral_pipeline",
    "default_pipeline",
    "leading_digit",
    "structural_groups",
]
