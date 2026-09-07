"""Preprocessing: chia dữ liệu theo thời gian.

Split phải tôn trọng trật tự thời gian để tránh leakage (RULE-27, RULE-28):
train < validation < test. Không shuffle.
"""

from __future__ import annotations

import pandas as pd

from sentinel.data.contracts import SplitData


def temporal_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    time_column: str = "Time",
) -> SplitData:
    """Chia DataFrame theo thời gian thành train/validation/test.

    Args:
        df: DataFrame chứa cột thời gian.
        train_ratio: Tỷ lệ phần train.
        validation_ratio: Tỷ lệ phần validation.
        time_column: Tên cột thời gian dùng để sắp xếp.

    Returns:
        SplitData chứa ba phần dữ liệu chia theo thời gian.

    Raises:
        ValueError: Nếu tổng tỷ lệ > 1 hoặc cột thời gian không tồn tại.
    """
    test_ratio = 1.0 - train_ratio - validation_ratio
    if test_ratio <= 0:
        raise ValueError(
            "Tổng train_ratio + validation_ratio phải < 1 để có phần test"
        )
    if time_column not in df.columns:
        raise ValueError(f"Thiếu cột thời gian: {time_column}")

    df_sorted = df.sort_values(time_column).reset_index(drop=True)
    n = len(df_sorted)

    train_end = int(n * train_ratio)
    validation_end = int(n * (train_ratio + validation_ratio))

    train = df_sorted.iloc[:train_end].reset_index(drop=True)
    validation = df_sorted.iloc[train_end:validation_end].reset_index(drop=True)
    test = df_sorted.iloc[validation_end:].reset_index(drop=True)

    metadata = {
        "train_ratio": train_ratio,
        "validation_ratio": validation_ratio,
        "test_ratio": round(test_ratio, 6),
        "n_train": len(train),
        "n_validation": len(validation),
        "n_test": len(test),
    }

    return SplitData(train=train, validation=validation, test=test, metadata=metadata)