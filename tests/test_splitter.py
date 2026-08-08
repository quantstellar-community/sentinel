"""Leakage tests.

These are the tests that matter most in Phase 0. A bug in a model costs an
experiment; a bug here silently invalidates every number the project will ever
produce, because the results still look plausible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import splitter
from src.data.preprocessor import NotFittedError, Preprocessor
from src.datasets import CREDITCARD
from tests.conftest import make_frame




# --------------------------------------------------------------------------
# Temporal ordering
# --------------------------------------------------------------------------


def test_train_strictly_precedes_test():
    before, after, cut = splitter.temporal_split(make_frame(), 0.8)
    assert before[CREDITCARD.time_column].max() <= cut < after[CREDITCARD.time_column].min()
    splitter.assert_no_temporal_leakage(before, after)


def test_tied_timestamps_never_straddle_a_cut():
    """The reason cuts are made on values, not on row positions."""
    df = make_frame(n=5_000, n_unique_times=50)
    before, after, _ = splitter.temporal_split(df, 0.8)

    shared = set(before[CREDITCARD.time_column]) & set(after[CREDITCARD.time_column])
    assert not shared, f"timestamps present on both sides of the cut: {sorted(shared)}"


def test_split_is_a_partition():
    df = make_frame()
    before, after, _ = splitter.temporal_split(df, 0.8)

    assert len(before) + len(after) == len(df)
    assert set(before.index).isdisjoint(after.index)


def test_leakage_assertion_catches_a_bad_split():
    """A positional split on tied timestamps is exactly what must be rejected."""
    df = make_frame(n=1_000, n_unique_times=20)
    bad_train, bad_test = df.iloc[:800], df.iloc[800:]

    with pytest.raises(splitter.SplitError, match="temporal leakage"):
        splitter.assert_no_temporal_leakage(bad_train, bad_test)


# --------------------------------------------------------------------------
# Expanding-window folds
# --------------------------------------------------------------------------


def test_folds_expand_and_stay_ordered():
    df = make_frame(n=10_000, n_unique_times=2_000)
    folds = splitter.expanding_window_folds(df, n_folds=4)

    assert len(folds) == 4
    for fold in folds:
        train, val = df.iloc[fold.train_idx], df.iloc[fold.val_idx]
        assert len(train) and len(val)
        splitter.assert_no_temporal_leakage(train, val)

    # Each fold trains on strictly more history than the one before it.
    sizes = [len(fold.train_idx) for fold in folds]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)


def test_validation_blocks_are_disjoint_and_cover_the_tail():
    df = make_frame(n=10_000, n_unique_times=2_000)
    folds = splitter.expanding_window_folds(df, n_folds=4)

    seen: set[int] = set()
    for fold in folds:
        current = set(fold.val_idx.tolist())
        assert seen.isdisjoint(current), "validation blocks overlap"
        seen |= current

    # Blocks 1..n together cover everything except the first block.
    assert max(seen) == len(df) - 1


def test_holdout_is_the_final_slice_of_time():
    df = make_frame(n=10_000, n_unique_times=2_000)
    dev, holdout, _ = splitter.dev_holdout_split(df, holdout_fraction=0.2)

    splitter.assert_no_temporal_leakage(dev, holdout)
    assert holdout[CREDITCARD.time_column].max() == df[CREDITCARD.time_column].max()
    assert 0.15 < len(holdout) / len(df) < 0.25


def test_rejects_degenerate_requests():
    df = make_frame()
    with pytest.raises(splitter.SplitError):
        splitter.temporal_split(df, 1.0)
    with pytest.raises(splitter.SplitError):
        splitter.expanding_window_folds(df, n_folds=0)


# --------------------------------------------------------------------------
# Preprocessing leakage
# --------------------------------------------------------------------------


def test_scaler_statistics_come_from_train_only():
    df = make_frame(n=4_000, n_unique_times=1_000)
    train, test, _ = splitter.temporal_split(df, 0.8)

    fitted_on_train = Preprocessor().fit(train)
    fitted_on_all = Preprocessor().fit(df)

    assert fitted_on_train.fitted_on_n_rows == len(train)

    # Transforming the test set must not reproduce what fitting on everything
    # would have given — if it does, train statistics were not actually used.
    from_train = fitted_on_train.transform(test)[CREDITCARD.amount_column].to_numpy()
    from_all = fitted_on_all.transform(test)[CREDITCARD.amount_column].to_numpy()
    assert not np.allclose(from_train, from_all)


def test_transform_does_not_refit():
    df = make_frame()
    train, test, _ = splitter.temporal_split(df, 0.8)

    pre = Preprocessor().fit(train)
    pre.transform(test)
    assert pre.fitted_on_n_rows == len(train), "transform() mutated the fitted state"


def test_transform_before_fit_raises():
    with pytest.raises(NotFittedError):
        Preprocessor().transform(make_frame())


def test_unscaled_columns_pass_through_untouched():
    df = make_frame()
    out = Preprocessor().fit_transform(df)

    for col in [f'V{i}' for i in range(1, 29)]:
        assert np.array_equal(out[col].to_numpy(), df[col].to_numpy())
    assert np.array_equal(out[CREDITCARD.target_column], df[CREDITCARD.target_column])
