"""Cấu hình Sentinel.

Settings được load từ file YAML trong `configs/` bằng PyYAML.
Settings chỉ chứa configuration value, không chứa business logic (RULE-56).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class DataConfig:
    raw_path: str = "data/raw/creditcard.csv"


@dataclass(frozen=True)
class PreprocessingConfig:
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    random_seed: int = 42
    feature_columns: list[str] = field(default_factory=list)
    target_column: str = "Class"


@dataclass(frozen=True)
class Settings:
    data: DataConfig
    preprocessing: PreprocessingConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> Settings:
        config_path = Path(path)
        with config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        data_raw = raw.get("data", {})
        preprocessing_raw = raw.get("preprocessing", {})

        return cls(
            data=DataConfig(**data_raw),
            preprocessing=PreprocessingConfig(**preprocessing_raw),
        )