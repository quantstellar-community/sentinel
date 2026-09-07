"""Validation: kiểm tra dữ liệu đầu vào.

Validation kiểm tra dữ liệu ở data boundary trước khi đi sâu vào pipeline
(RULE-40). Không chứa business logic.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["Time", "Amount", "Class"]


class DataValidationError(ValueError):
    """Lỗi khi dữ liệu không đạt điều kiện validation."""


def validate_creditcard(df: pd.DataFrame) -> None:
    """Kiểm tra dữ liệu credit-card có hợp lệ không.

    Args:
        df: DataFrame thô cần kiểm tra.

    Raises:
        DataValidationError: Nếu thiếu cột bắt buộc, có giá trị null,
            hoặc cột Class không phải binary.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"Thiếu cột bắt buộc: {missing}. Có cần: {REQUIRED_COLUMNS}"
        )

    if df[REQUIRED_COLUMNS].isnull().any().any():
        raise DataValidationError("Dữ liệu có giá trị null ở cột bắt buộc.")

    class_values = df["Class"].dropna().unique()
    if not set(class_values).issubset({0, 1}):
        raise DataValidationError(f"Class phải là binary (0/1), nhận được: {sorted(class_values)}")