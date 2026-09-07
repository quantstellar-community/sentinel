"""Preprocessing: xây dựng feature representation.

Feature engineering là derived data, tách khỏi raw data (RULE-18).
Scaler chỉ được fit trên train, transform lên validation/test để tránh
feature leakage (RULE-28).
"""

from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import StandardScaler

from sentinel.data.contracts import SplitData

# Các cột PCA features của European credit-card dataset.
PCA_FEATURE_PREFIX = "V"
AMOUNT_COLUMN = "Amount"


def auto_detect_feature_columns(df: pd.DataFrame) -> list[str]:
    """Tự nhận diện feature columns: V1..V28 + Amount.

    Args:
        df: DataFrame chứa cột features.

    Returns:
        Danh sách tên feature columns theo thứ tự V1..V28 + Amount.
    """
    pca_columns = sorted(
        [c for c in df.columns if c.startswith(PCA_FEATURE_PREFIX)],
        key=lambda c: int(c[len(PCA_FEATURE_PREFIX):]),
    )
    if AMOUNT_COLUMN in df.columns:
        pca_columns.append(AMOUNT_COLUMN)
    return pca_columns


def build_features(
    split: SplitData,
    feature_columns: list[str] | None = None,
    target_column: str = "Class",
) -> SplitData:
    """Chọn feature columns và scale Amount trên toàn bộ split.

    Scaler fit trên train, transform validation/test bằng cùng scaler
    (tránh leakage). V1..V28 đã được PCA scaling sẵn nên chỉ scale Amount.

    Args:
        split: SplitData từ temporal_split.
        feature_columns: Danh sách feature. None => auto-detect V1..V28 + Amount.
        target_column: Cột target giữ nguyên (không scale, không làm feature).

    Returns:
        SplitData mới với feature columns đã scale, metadata bổ sung.
    """
    if feature_columns is None:
        feature_columns = auto_detect_feature_columns(split.train)

    missing = [c for c in feature_columns if c not in split.train.columns]
    if missing:
        raise ValueError(f"Thiếu feature columns trong train: {missing}")

    # Chỉ scale Amount; V1..V28 đã PCA-scaled sẵn.
    scale_columns = [AMOUNT_COLUMN] if AMOUNT_COLUMN in feature_columns else []
    scaler = StandardScaler()
    if scale_columns:
        scaler.fit(split.train[scale_columns])

    def transform(df: pd.DataFrame) -> pd.DataFrame:
        out = df[feature_columns].copy()
        if scale_columns:
            out[scale_columns] = scaler.transform(df[scale_columns])
        if target_column in df.columns:
            out[target_column] = df[target_column].values
        return out

    train = transform(split.train)
    validation = transform(split.validation)
    test = transform(split.test)

    metadata = dict(split.metadata)
    metadata.update(
        {
            "feature_columns": feature_columns,
            "target_column": target_column,
            "scaled_columns": scale_columns,
            "scaler": "StandardScaler" if scale_columns else None,
        }
    )

    return SplitData(
        train=train,
        validation=validation,
        test=test,
        feature_columns=feature_columns,
        metadata=metadata,
    )