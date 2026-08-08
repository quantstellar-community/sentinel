"""Layer 4 tests.

Two properties matter most here and both are invisible in a metrics table:

1.  A group must learn nothing from the evaluation fold. The test for that is
    not "does fit() take train" — it is that removing future rows leaves the
    present row's features unchanged.
2.  Structural groups must not alter the feature space on a dataset that has no
    strings and no missing values. That is what keeps the recorded creditcard
    results reproducible now that this layer exists.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import CREDITCARD, IEEECIS, DatasetSpec
from src.features import (
    MISSING_CODE,
    UNSEEN_CODE,
    CategoricalEncode,
    FeatureError,
    FeaturePipeline,
    NotFittedError,
    PassThrough,
    TimeOfDay,
    default_pipeline,
    structural_groups,
)
from tests.conftest import make_dev, make_frame


def frame_with_strings(n: int = 400, seed: int = 0) -> pd.DataFrame:
    """An IEEE-shaped frame carrying the two things creditcard never has:
    string columns and missing values."""
    rng = np.random.default_rng(seed)
    base = make_frame(IEEECIS, n=n, n_unique_times=200, seed=seed)

    base["ProductCD"] = rng.choice(["W", "C", "H"], size=n)
    base["DeviceType"] = rng.choice(["mobile", "desktop", None], size=n)
    base["V1"] = base["V1"].mask(rng.random(n) < 0.4)
    return base


# --------------------------------------------------------------------------
# The reproduction guarantee
# --------------------------------------------------------------------------


def test_structural_pipeline_is_the_identity_on_a_clean_numeric_dataset():
    """creditcard has no strings and no NaN, so the default pipeline must hand
    back exactly the columns the old code path produced — same names, same
    order. This is what keeps the recorded results reproducible."""
    df = make_dev(CREDITCARD)
    X = default_pipeline(CREDITCARD).fit_transform(df)

    expected = [c for c in df.columns if c != CREDITCARD.target_column]
    assert list(X.columns) == expected
    assert len(X.columns) == 30

    for column in expected:
        assert np.array_equal(X[column].to_numpy(), df[column].to_numpy())


def test_default_pipeline_contains_no_derived_groups():
    """A derived group changes the feature space and therefore every downstream
    number, so it cannot be switched on silently."""
    assert all(not group.derived for group in structural_groups())


# --------------------------------------------------------------------------
# PassThrough
# --------------------------------------------------------------------------


def test_passthrough_excludes_target_and_join_key():
    """A row identifier carries no signal but correlates with time, which makes
    it an excellent way to leak split ordering into a tree."""
    df = frame_with_strings()
    columns = PassThrough().fit(df, IEEECIS).output_columns()

    assert IEEECIS.target_column not in columns
    assert IEEECIS.join_key not in columns


def test_passthrough_excludes_string_columns():
    df = frame_with_strings()
    columns = PassThrough().fit(df, IEEECIS).output_columns()

    assert "ProductCD" not in columns
    assert "DeviceType" not in columns


def test_passthrough_before_fit_raises():
    with pytest.raises(NotFittedError):
        PassThrough().output_columns()


# --------------------------------------------------------------------------
# CategoricalEncode
# --------------------------------------------------------------------------


def test_categorical_encode_is_a_noop_without_strings():
    df = make_dev(CREDITCARD)
    group = CategoricalEncode().fit(df, CREDITCARD)

    assert group.output_columns() == []
    assert group.transform(df).shape[1] == 0


def test_categorical_encode_covers_every_string_column():
    df = frame_with_strings()
    columns = CategoricalEncode().fit(df, IEEECIS).output_columns()

    assert "ProductCD" in columns
    assert "DeviceType" in columns
    assert IEEECIS.target_column not in columns


def test_encoded_output_is_numeric():
    df = frame_with_strings()
    encoded = CategoricalEncode().fit(df, IEEECIS).transform(df)

    for column in encoded.columns:
        assert pd.api.types.is_integer_dtype(encoded[column])


def test_vocabulary_comes_from_train_only():
    """Fitting the encoder on the whole frame would tell the model which
    categories are going to appear in the future."""
    train = pd.DataFrame(
        {
            "ProductCD": ["W", "C"],
            IEEECIS.time_column: [1.0, 2.0],
            IEEECIS.amount_column: [1.0, 2.0],
            IEEECIS.target_column: [0, 0],
        }
    )
    future = train.copy()
    future["ProductCD"] = ["W", "BRAND_NEW"]

    group = CategoricalEncode().fit(train, IEEECIS)
    encoded = group.transform(future)["ProductCD"].tolist()

    assert encoded[0] >= 0, "a value seen in training keeps its code"
    assert encoded[1] == UNSEEN_CODE, "a value absent from training is marked unseen"


def test_missing_and_unseen_carry_different_codes():
    """Absent and never-seen are different signals; collapsing them would throw
    away the distinction for no benefit."""
    train = pd.DataFrame(
        {
            "ProductCD": ["W", "C"],
            IEEECIS.time_column: [1.0, 2.0],
            IEEECIS.amount_column: [1.0, 2.0],
            IEEECIS.target_column: [0, 0],
        }
    )
    later = train.copy()
    later["ProductCD"] = [None, "NEW"]

    encoded = CategoricalEncode().fit(train, IEEECIS).transform(later)["ProductCD"].tolist()

    assert encoded[0] == MISSING_CODE
    assert encoded[1] == UNSEEN_CODE
    assert MISSING_CODE != UNSEEN_CODE


# --------------------------------------------------------------------------
# The leakage property — the one that matters
# --------------------------------------------------------------------------


def test_transform_of_a_row_does_not_depend_on_later_rows():
    """The real leakage test.

    Not "does fit() take train" — that is trivially satisfiable by an
    implementation that still peeks. What must hold is that deleting the future
    leaves the present unchanged.
    """
    df = frame_with_strings(n=400)
    pipeline = default_pipeline(IEEECIS).fit(df.iloc[:200])

    full = pipeline.transform(df.iloc[:200])
    truncated = pipeline.transform(df.iloc[:150])

    pd.testing.assert_frame_equal(full.iloc[:150], truncated)


def test_pipeline_fit_never_sees_the_evaluation_fold():
    seen: list[int] = []

    class Spy(PassThrough):
        name = "spy"

        def fit(self, train, spec):
            seen.append(len(train))
            return super().fit(train, spec)

    df = make_dev(CREDITCARD)
    train, val = df.iloc[:2_000], df.iloc[2_000:]

    pipeline = FeaturePipeline([Spy()], CREDITCARD).fit(train)
    pipeline.transform(val)

    assert seen == [len(train)], "fit was called with something other than train"


# --------------------------------------------------------------------------
# applies_to — one group list, every dataset
# --------------------------------------------------------------------------


def test_entity_groups_exclude_themselves_when_there_is_no_entity():
    class NeedsEntity(PassThrough):
        name = "needs_entity"
        requires_entity = True

    groups = [PassThrough(), NeedsEntity()]

    assert len(FeaturePipeline(groups, CREDITCARD).groups) == 1
    assert FeaturePipeline(groups, CREDITCARD).skipped == ["needs_entity"]
    assert len(FeaturePipeline(groups, IEEECIS).groups) == 2


def test_same_group_list_serves_both_datasets():
    """The point of applies_to: no per-dataset configuration."""
    for spec in (CREDITCARD, IEEECIS):
        pipeline = FeaturePipeline(structural_groups(), spec)
        assert pipeline.groups, f"no groups applied to {spec.name}"


# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------


def test_duplicate_output_columns_are_rejected():
    df = make_dev(CREDITCARD)

    with pytest.raises(FeatureError, match="produced by both"):
        FeaturePipeline([PassThrough(), PassThrough()], CREDITCARD).fit(df)


def test_transform_before_fit_raises():
    with pytest.raises(NotFittedError):
        default_pipeline(CREDITCARD).transform(make_dev(CREDITCARD))


def test_output_column_order_is_deterministic():
    df = frame_with_strings()
    first = default_pipeline(IEEECIS).fit(df).output_columns()
    second = default_pipeline(IEEECIS).fit(df).output_columns()

    assert first == second


def test_describe_is_json_serializable():
    import json

    df = frame_with_strings()
    pipeline = default_pipeline(IEEECIS).fit(df)
    json.dumps(pipeline.describe())


# --------------------------------------------------------------------------
# TimeOfDay — opt-in on purpose
# --------------------------------------------------------------------------


def test_time_of_day_is_derived_and_opt_in():
    assert TimeOfDay().derived is True
    assert "time_of_day" not in [g.name for g in structural_groups()]


def test_time_of_day_computes_the_cycle(any_spec: DatasetSpec):
    df = make_frame(any_spec, n=100, n_unique_times=100)
    out = TimeOfDay().fit(df, any_spec).transform(df)

    assert list(out.columns) == ["HOUR_OF_DAY", "DAY_OF_WEEK"]
    assert out["HOUR_OF_DAY"].between(0, 23).all()
    assert out["DAY_OF_WEEK"].between(0, 6).all()
