"""Layer 2 — Ingestion: raw files to a canonical frame, or a hard stop.

Five steps, in order: load, join, validate, dedup, sort. There is no
intermediate "close enough" state — either the frame matches the declared
contract or the program raises.

The strictness is deliberate. When the file on disk drifts from what the
documentation describes, every downstream number is wrong while still *looking*
reasonable. Stopping is better than producing a figure nobody knows is false.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.datasets import DatasetSpec, get_spec


class DataContractError(ValueError):
    """Raised when the data on disk does not match the declared contract."""


@dataclass(frozen=True)
class LoadReport:
    """Exactly what the loader did, for the manifest and the audit trail."""

    dataset: str
    tables: dict[str, str]
    sha256: dict[str, str]
    n_rows_raw: int
    n_fraud_raw: int
    n_duplicates_dropped: int
    n_fraud_duplicates_dropped: int
    n_rows: int
    n_fraud: int
    fraud_rate: float
    time_min: float
    time_max: float
    n_columns: int

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    """Content hash of a source file, recorded so results stay traceable."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Step 3 — validation
# --------------------------------------------------------------------------


def validate(df: pd.DataFrame, spec: DatasetSpec, *, strict: bool = True) -> None:
    """Check a freshly-read frame against the spec.

    `strict=False` skips the row and fraud counts, which lets tests and
    subsample experiments run while still validating structure.
    """
    if spec.expected_columns and list(df.columns) != spec.expected_columns:
        missing = set(spec.expected_columns) - set(df.columns)
        extra = set(df.columns) - set(spec.expected_columns)
        raise DataContractError(
            f"{spec.name}: column mismatch — missing={sorted(missing)} "
            f"extra={sorted(extra)} (order matters when expected_columns is set)"
        )

    required = spec.required_columns or list(df.columns)
    absent = [c for c in required if c not in df.columns]
    if absent:
        raise DataContractError(f"{spec.name}: required columns absent: {absent}")

    nulls = df[required].isnull().sum()
    offenders = nulls[nulls > 0]
    if len(offenders):
        raise DataContractError(
            f"{spec.name}: required columns contain nulls: {offenders.to_dict()}"
        )

    for column in (spec.time_column, spec.amount_column):
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise DataContractError(f"{spec.name}: {column} is not numeric")
        if (df[column] < 0).any():
            raise DataContractError(f"{spec.name}: {column} contains negative values")

    labels = set(df[spec.target_column].unique().tolist())
    if not labels <= {0, 1}:
        raise DataContractError(
            f"{spec.name}: {spec.target_column} must be binary, found {sorted(labels)}"
        )

    if spec.has_entity:
        absent_keys = [k for k in spec.entity_keys or [] if k not in df.columns]
        if absent_keys:
            raise DataContractError(
                f"{spec.name}: declared entity_keys not in data: {absent_keys}"
            )

    if not strict:
        return

    if spec.expected_rows and len(df) != spec.expected_rows:
        raise DataContractError(
            f"{spec.name}: expected {spec.expected_rows:,} rows, found {len(df):,}. "
            "If the data was intentionally replaced, update the DatasetSpec and "
            "the documentation together."
        )

    n_fraud = int(df[spec.target_column].sum())
    if spec.expected_fraud and n_fraud != spec.expected_fraud:
        raise DataContractError(
            f"{spec.name}: expected {spec.expected_fraud:,} fraud rows, found {n_fraud:,}"
        )


# --------------------------------------------------------------------------
# Steps 1-5
# --------------------------------------------------------------------------


def load_raw(
    spec: DatasetSpec | str | None = None,
    *,
    drop_duplicates: bool | None = None,
    validate_contract: bool = True,
    strict: bool = True,
    compute_hash: bool = True,
    paths: dict[str, Path] | None = None,
) -> tuple[pd.DataFrame, LoadReport]:
    """Read, join, validate, dedup, and sort. Returns the frame and a report.

    `paths` overrides `spec.raw_paths`, which is what lets tests exercise the
    real code path against synthetic files.
    """
    spec = get_spec(spec)
    raw_paths = {k: Path(v) for k, v in (paths or spec.raw_paths).items()}

    for name, path in raw_paths.items():
        if not path.exists():
            raise FileNotFoundError(
                f"{spec.name}: table {name!r} not found at {path}. "
                "Datasets are gitignored; see docs/project_guide.md for sources."
            )

    # --- 1. Load ------------------------------------------------------
    primary_name = next(iter(raw_paths))
    df = pd.read_csv(raw_paths[primary_name])

    # --- 2. Join (LEFT, always) ---------------------------------------
    # Secondary tables cover only part of the primary one. An inner join would
    # silently discard most rows; a left join keeps them and leaves NaN, and
    # "no identity data was collected for this transaction" is itself a signal.
    for name, path in list(raw_paths.items())[1:]:
        secondary = pd.read_csv(path)
        if spec.join_key not in df.columns or spec.join_key not in secondary.columns:
            raise DataContractError(
                f"{spec.name}: join_key {spec.join_key!r} missing from "
                f"{'primary' if spec.join_key not in df.columns else name}"
            )
        before = len(df)
        df = df.merge(secondary, on=spec.join_key, how="left", suffixes=("", f"_{name}"))
        if len(df) != before:
            raise DataContractError(
                f"{spec.name}: joining {name!r} changed the row count "
                f"({before:,} -> {len(df):,}); {spec.join_key} is not unique there"
            )

    # The target may arrive quoted in the raw file.
    df[spec.target_column] = df[spec.target_column].astype("int64")

    # --- 3. Validate --------------------------------------------------
    if validate_contract:
        validate(df, spec, strict=strict)

    n_rows_raw = len(df)
    n_fraud_raw = int(df[spec.target_column].sum())

    # --- 4. Dedup -----------------------------------------------------
    drop_duplicates = spec.drop_exact_duplicates if drop_duplicates is None else drop_duplicates
    n_dupes = n_fraud_dupes = 0
    if drop_duplicates:
        duplicated = df.duplicated(keep="first")
        n_dupes = int(duplicated.sum())
        n_fraud_dupes = int(df.loc[duplicated, spec.target_column].sum())
        df = df.loc[~duplicated]

    # --- 5. Sort ------------------------------------------------------
    # Stable: many rows share a timestamp, and original file order is the only
    # ordering information left inside a tie group. It has to be deterministic
    # for results to reproduce.
    df = df.sort_values(spec.time_column, kind="stable").reset_index(drop=True)

    report = LoadReport(
        dataset=spec.name,
        tables={k: str(v) for k, v in raw_paths.items()},
        sha256={k: sha256_of(v) for k, v in raw_paths.items()} if compute_hash else {},
        n_rows_raw=n_rows_raw,
        n_fraud_raw=n_fraud_raw,
        n_duplicates_dropped=n_dupes,
        n_fraud_duplicates_dropped=n_fraud_dupes,
        n_rows=len(df),
        n_fraud=int(df[spec.target_column].sum()),
        fraud_rate=float(df[spec.target_column].mean()),
        time_min=float(df[spec.time_column].min()),
        time_max=float(df[spec.time_column].max()),
        n_columns=int(df.shape[1]),
    )
    return df, report


# --------------------------------------------------------------------------
# Feature / target separation and split I/O
# --------------------------------------------------------------------------


def split_xy(df: pd.DataFrame, spec: DatasetSpec | str | None = None):
    """Separate features from the target.

    Everything that is not the target and not a join key is a candidate
    feature; the feature pipeline and the model narrow it further.
    """
    spec = get_spec(spec)
    dropped = [spec.target_column]
    if spec.join_key and spec.join_key in df.columns:
        dropped.append(spec.join_key)

    features = [c for c in df.columns if c not in dropped]
    return df[features].copy(), df[spec.target_column].copy()


def load_split(split_name: str, spec: DatasetSpec | str | None = None) -> pd.DataFrame:
    """Read a materialized split written by `scripts/build_splits.py`."""
    spec = get_spec(spec)
    path = spec.split_path(split_name)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: "
            f"uv run python scripts/build_splits.py --dataset {spec.name}"
        )
    return pd.read_parquet(path)


def read_manifest(spec: DatasetSpec | str | None = None) -> dict:
    """The split manifest — what was cut where, from which source files."""
    spec = get_spec(spec)
    path = spec.split_manifest_path
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: "
            f"uv run python scripts/build_splits.py --dataset {spec.name}"
        )
    return json.loads(path.read_text(encoding="utf-8"))
