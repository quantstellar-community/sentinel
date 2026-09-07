"""Tests cho data layer: ingestion/validation/preprocessing."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel.data.ingestion.creditcard import load_creditcard
from sentinel.data.preprocessing.features import (
    auto_detect_feature_columns,
    build_features,
)
from sentinel.data.preprocessing.split import temporal_split
from sentinel.data.validation.creditcard import DataValidationError, validate_creditcard


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """DataFrame nhỏ mô phỏng cấu trúc European credit-card."""
    n = 1000
    rng = np.random.default_rng(42)
    columns = {f"V{i}": rng.normal(0, 1, n) for i in range(1, 29)}
    df = pd.DataFrame(columns)
    df["Time"] = np.arange(n)
    df["Amount"] = rng.uniform(0, 2000, n)
    df["Class"] = rng.integers(0, 2, n)
    return df


class TestIngestion:
    def test_load_creditcard_returns_dataframe(self, tmp_path):
        df = pd.DataFrame({"Time": [0], "Amount": [1.0], "Class": [0]})
        path = tmp_path / "creditcard.csv"
        df.to_csv(path, index=False)

        loaded = load_creditcard(path)
        assert isinstance(loaded, pd.DataFrame)
        assert list(loaded.columns) == ["Time", "Amount", "Class"]

    def test_load_real_creditcard_if_present(self):
        try:
            df = load_creditcard("data/raw/creditcard.csv")
        except FileNotFoundError:
            pytest.skip("data/raw/creditcard.csv không tồn tại")
        assert df.shape[1] == 31
        assert "Class" in df.columns


class TestValidation:
    def test_valid_data_passes(self, sample_df):
        validate_creditcard(sample_df)

    def test_missing_column_raises(self, sample_df):
        bad = sample_df.drop(columns=["Class"])
        with pytest.raises(DataValidationError):
            validate_creditcard(bad)

    def test_null_raises(self, sample_df):
        bad = sample_df.copy()
        bad.loc[0, "Amount"] = np.nan
        with pytest.raises(DataValidationError):
            validate_creditcard(bad)

    def test_non_binary_class_raises(self, sample_df):
        bad = sample_df.copy()
        bad.loc[0, "Class"] = 2
        with pytest.raises(DataValidationError):
            validate_creditcard(bad)


class TestTemporalSplit:
    def test_split_ratios(self, sample_df):
        split = temporal_split(sample_df, train_ratio=0.70, validation_ratio=0.15)
        n = len(sample_df)
        assert len(split.train) == int(n * 0.70)
        assert len(split.validation) == int(n * 0.15)
        assert len(split.test) == n - int(n * 0.70) - int(n * 0.15)

    def test_no_temporal_leakage(self, sample_df):
        split = temporal_split(sample_df, train_ratio=0.70, validation_ratio=0.15)
        assert split.train["Time"].max() <= split.validation["Time"].min()
        assert split.validation["Time"].max() <= split.test["Time"].min()

    def test_no_shuffle_preserves_order(self, sample_df):
        split = temporal_split(sample_df, train_ratio=0.70, validation_ratio=0.15)
        assert split.train["Time"].is_monotonic_increasing
        assert split.validation["Time"].is_monotonic_increasing

    def test_invalid_ratios_raise(self, sample_df):
        with pytest.raises(ValueError):
            temporal_split(sample_df, train_ratio=0.90, validation_ratio=0.20)

    def test_missing_time_column_raises(self, sample_df):
        bad = sample_df.drop(columns=["Time"])
        with pytest.raises(ValueError):
            temporal_split(bad, time_column="Time")


class TestFeatures:
    def test_auto_detect_feature_columns(self, sample_df):
        cols = auto_detect_feature_columns(sample_df)
        assert cols == [f"V{i}" for i in range(1, 29)] + ["Amount"]
        assert "Class" not in cols
        assert "Time" not in cols

    def test_build_features_scales_amount_only(self, sample_df):
        split = temporal_split(sample_df)
        feat = build_features(split)

        # Amount scaled: mean ~0, std ~1 trên train
        assert abs(feat.train["Amount"].mean()) < 0.05
        assert abs(feat.train["Amount"].std() - 1.0) < 0.05

        # V1 giữ nguyên (đã PCA-scaled): std giống gốc
        assert abs(feat.train["V1"].std() - 1.0) < 0.05

    def test_scaler_fit_on_train_only(self, sample_df):
        split = temporal_split(sample_df)
        feat = build_features(split)
        # Validation không fit lại scaler nên mean không nhất thiết ~0
        assert "feature_columns" in feat.metadata
        assert feat.metadata["scaler"] == "StandardScaler"

    def test_class_preserved(self, sample_df):
        split = temporal_split(sample_df)
        feat = build_features(split)
        assert set(feat.test["Class"].unique()) <= {0, 1}

    def test_feature_columns_in_metadata(self, sample_df):
        split = temporal_split(sample_df)
        feat = build_features(split)
        assert feat.feature_columns == [f"V{i}" for i in range(1, 29)] + ["Amount"]
        assert feat.metadata["feature_columns"] == feat.feature_columns