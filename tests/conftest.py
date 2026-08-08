"""Shared fixtures.

Every test frame is generated *from a spec* rather than hardcoding one
dataset's columns. That is what lets the same test body run against creditcard
and IEEE-CIS, and it is how the suite would catch a layer that quietly assumed
creditcard's schema.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import CREDITCARD, IEEECIS, DatasetSpec


def make_frame(
    spec: DatasetSpec = CREDITCARD,
    n: int = 1_000,
    *,
    n_unique_times: int = 200,
    fraud_rate: float = 0.02,
    n_numeric: int = 28,
    n_entities: int = 40,
    signal_strength: float = 0.0,
    seed: int = 0,
) -> pd.DataFrame:
    """A frame shaped like `spec`: right column roles, right dtypes.

    `signal_strength > 0` plants separable structure in the first few numeric
    columns, which is what lets a test assert that a model ranks fraud above
    normal without asserting any particular quality bar.
    """
    rng = np.random.default_rng(seed)

    times = np.sort(rng.integers(0, n_unique_times, size=n)).astype(float)
    label = (rng.random(n) < fraud_rate).astype(int)

    data: dict[str, np.ndarray] = {spec.time_column: times}
    for i in range(n_numeric):
        signal = signal_strength * label if i < 4 else 0.0
        data[f"V{i + 1}"] = rng.normal(size=n) + signal

    amount = rng.exponential(80.0, size=n)
    if signal_strength > 0 and spec.has_entity:
        # Fraud spends far above the entity's own norm. This is the behavioural
        # signal the z-score and velocity columns exist to see, and planting it
        # is what makes an assertion about a behavioural-only model meaningful —
        # without it such a model ranks pure noise and "fraud scores higher"
        # would be asserting nothing.
        amount = amount * np.where(label == 1, 1.0 + 25.0 * signal_strength, 1.0)
    data[spec.amount_column] = amount

    if spec.has_entity:
        # Composite key: several columns whose combination identifies an entity.
        entity = rng.integers(0, n_entities, size=n)
        for offset, key in enumerate(spec.entity_keys or []):
            data[key] = (entity + offset * 1000).astype(float)

    if spec.join_key:
        data[spec.join_key] = np.arange(n, dtype="int64")

    data[spec.target_column] = label

    frame = pd.DataFrame(data)
    ordered = spec.expected_columns or list(frame.columns)
    return frame[[c for c in ordered if c in frame.columns]]


def make_dev(
    spec: DatasetSpec = CREDITCARD,
    n: int = 3_000,
    *,
    n_unique_times: int = 1_500,
    fraud_rate: float = 0.05,
    seed: int = 0,
    **kwargs,
) -> pd.DataFrame:
    """A development split with enough fraud and enough signal to fit on."""
    return make_frame(
        spec,
        n=n,
        n_unique_times=n_unique_times,
        fraud_rate=fraud_rate,
        signal_strength=kwargs.pop("signal_strength", 1.2),
        seed=seed,
        **kwargs,
    )


@pytest.fixture
def creditcard_spec() -> DatasetSpec:
    return CREDITCARD


@pytest.fixture
def ieeecis_spec() -> DatasetSpec:
    return IEEECIS


@pytest.fixture(params=[CREDITCARD, IEEECIS], ids=["creditcard", "ieeecis"])
def any_spec(request) -> DatasetSpec:
    """Runs a test against both dataset shapes.

    The point is the entity axis: one spec declares entity keys and one does
    not, so anything that silently assumes either will fail here.
    """
    return request.param


@pytest.fixture
def dev_frame(any_spec: DatasetSpec) -> pd.DataFrame:
    return make_dev(any_spec)
