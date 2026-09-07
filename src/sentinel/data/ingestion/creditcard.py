"""Ingestion: load dữ liệu thô từ nguồn.

Data layer chỉ load và trả về dữ liệu thô (chưa xử lý), không chứa
decision logic (RULE-18).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_creditcard(path: str | Path) -> pd.DataFrame:
    """Load dataset credit-card từ file CSV.

    Args:
        path: Đường dẫn tới file CSV (thường là data/raw/creditcard.csv).

    Returns:
        DataFrame chứa dữ liệu thô, chưa qua xử lý.
    """
    return pd.read_csv(path)