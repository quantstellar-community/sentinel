"""Data-contract tests. These run on synthetic files so they need no dataset."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import loader
from src.datasets import CREDITCARD
from tests.conftest import make_frame


def write_csv(tmp_path, df: pd.DataFrame):
    """Write a synthetic frame and return the override the loader accepts.

    Tests exercise the real code path — spec-driven validation included — by
    overriding only where the files live.
    """
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return {"transaction": path}


def valid_frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    return make_frame(CREDITCARD, n=n, n_unique_times=100, fraud_rate=0.05, seed=seed)


def test_accepts_a_conforming_file(tmp_path):
    path = write_csv(tmp_path, valid_frame())
    df, report = loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)

    assert list(df.columns) == CREDITCARD.expected_columns
    assert report.n_rows == len(df)


def test_rejects_missing_columns(tmp_path):
    path = write_csv(tmp_path, valid_frame().drop(columns=["V7"]))
    with pytest.raises(loader.DataContractError, match="column mismatch"):
        loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)


def test_rejects_reordered_columns(tmp_path):
    """Order is part of the contract: several downstream steps index by position."""
    reordered = valid_frame()[[CREDITCARD.amount_column, *[f'V{i}' for i in range(1, 29)],
                               CREDITCARD.time_column, CREDITCARD.target_column]]
    path = write_csv(tmp_path, reordered)

    with pytest.raises(loader.DataContractError, match="order matters"):
        loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)


def test_rejects_nulls(tmp_path):
    df = valid_frame()
    df.loc[5, "V3"] = np.nan
    path = write_csv(tmp_path, df)

    with pytest.raises(loader.DataContractError, match="contain nulls"):
        loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)


def test_rejects_non_binary_target(tmp_path):
    df = valid_frame()
    df.loc[5, CREDITCARD.target_column] = 2
    path = write_csv(tmp_path, df)

    with pytest.raises(loader.DataContractError, match="must be binary"):
        loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)


def test_strict_mode_rejects_a_dataset_of_the_wrong_size(tmp_path):
    """Guards against quietly running against a subsample or a replaced file."""
    path = write_csv(tmp_path, valid_frame())
    with pytest.raises(loader.DataContractError, match="rows"):
        loader.load_raw(CREDITCARD, paths=path, strict=True, compute_hash=False)


def test_exact_duplicates_are_dropped_and_counted(tmp_path):
    df = valid_frame(n=100)
    df.loc[0, CREDITCARD.target_column] = 1
    doubled = pd.concat([df, df.iloc[:10]], ignore_index=True)
    path = write_csv(tmp_path, doubled)

    kept, report = loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)

    assert report.n_duplicates_dropped == 10
    assert report.n_fraud_duplicates_dropped == int(df.iloc[:10][CREDITCARD.target_column].sum())
    assert len(kept) == len(df)


def test_duplicates_can_be_kept(tmp_path):
    df = valid_frame(n=50)
    path = write_csv(tmp_path, pd.concat([df, df.iloc[:5]], ignore_index=True))

    kept, report = loader.load_raw(CREDITCARD, paths=path, drop_duplicates=False, strict=False, compute_hash=False
    )
    assert report.n_duplicates_dropped == 0
    assert len(kept) == 55


def test_rows_come_back_sorted_by_time(tmp_path):
    shuffled = valid_frame(n=300).sample(frac=1.0, random_state=1)
    path = write_csv(tmp_path, shuffled)

    df, _ = loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)
    assert df[CREDITCARD.time_column].is_monotonic_increasing


def test_missing_file_points_at_the_source(tmp_path):
    with pytest.raises(FileNotFoundError, match="gitignored"):
        loader.load_raw(CREDITCARD, paths={"transaction": tmp_path / "nope.csv"})


def test_split_xy_preserves_contract_order(tmp_path):
    path = write_csv(tmp_path, valid_frame())
    df, _ = loader.load_raw(CREDITCARD, paths=path, strict=False, compute_hash=False)

    X, y = loader.split_xy(df, CREDITCARD)
    assert list(X.columns) == [c for c in CREDITCARD.expected_columns if c != CREDITCARD.target_column]
    assert y.name == CREDITCARD.target_column
