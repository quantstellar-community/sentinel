"""Layer 1 — Domain Adapter: the registry of dataset declarations."""

from __future__ import annotations

from src.datasets.creditcard import CREDITCARD
from src.datasets.ieeecis import IEEECIS, IEEECIS_CARD1
from src.datasets.spec import (
    DATASETS_DIR,
    DEV_SPLIT_NAME,
    ENTITY_MISSING,
    EXPERIMENTS_ROOT,
    HOLDOUT_SPLIT_NAME,
    PROCESSED_ROOT,
    PROJECT_ROOT,
    DatasetError,
    DatasetSpec,
)

SPECS: dict[str, DatasetSpec] = {
    CREDITCARD.name: CREDITCARD,
    IEEECIS.name: IEEECIS,
    IEEECIS_CARD1.name: IEEECIS_CARD1,
}

#: The default when a command line omits `--dataset`. creditcard stays the
#: default because every recorded result so far is on it; changing this silently
#: would make old and new numbers look comparable when they are not.
DEFAULT_DATASET = CREDITCARD.name


def get_spec(name: str | DatasetSpec | None = None) -> DatasetSpec:
    """Resolve a dataset by name. Accepts a spec unchanged for convenience."""
    if isinstance(name, DatasetSpec):
        return name
    if name is None:
        return SPECS[DEFAULT_DATASET]
    if name not in SPECS:
        raise KeyError(f"unknown dataset {name!r}; available: {sorted(SPECS)}")
    return SPECS[name]


__all__ = [
    "CREDITCARD",
    "DATASETS_DIR",
    "DEFAULT_DATASET",
    "DEV_SPLIT_NAME",
    "ENTITY_MISSING",
    "EXPERIMENTS_ROOT",
    "HOLDOUT_SPLIT_NAME",
    "IEEECIS",
    "IEEECIS_CARD1",
    "PROCESSED_ROOT",
    "PROJECT_ROOT",
    "SPECS",
    "DatasetError",
    "DatasetSpec",
    "get_spec",
]
