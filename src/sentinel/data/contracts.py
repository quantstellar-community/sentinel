"""Data contracts của Sentinel.

Các contract này định nghĩa ranh giới giữa data layer và tầng trên
(models/evaluation) — tầng trên chỉ nhìn vào contract này, không phụ thuộc
dataset cụ thể (RULE-19, RULE-20).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class SplitData:
    """Output chuẩn của data layer.

    Chứa ba phần dữ liệu được chia theo thời gian (train < validation < test),
    danh sách feature columns và metadata để tái lập kết quả (RULE-25).
    """

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    feature_columns: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)