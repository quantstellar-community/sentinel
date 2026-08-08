"""Measure a dataset before its spec is finalised.

    uv run python scripts/profile_dataset.py --dataset ieeecis

Answers the questions a `DatasetSpec` has to declare — duplicate rows, entity
proxy quality, missingness, fold arithmetic — with numbers instead of
assumptions. Run it before editing a spec, not after.

**On choosing an entity proxy.** When a dataset carries no real customer
identifier, some combination of columns has to stand in for one. Candidates are
compared on *label-free* criteria only: how many groups, how long their
histories are, how many are singletons. Fraud concentration is printed as a
diagnostic but deliberately does **not** drive the choice — picking the entity
definition by how well it separates fraud would leak label information into
every behavioural feature built on top of it, and that leak would be invisible
in the results.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.data import loader
from src.datasets import ENTITY_MISSING, SPECS, DatasetSpec, get_spec

#: Column-name prefixes worth summarising separately on wide datasets.
COLUMN_GROUPS = {
    "C (counting)": lambda c: c.startswith("C") and c[1:].isdigit(),
    "D (timedelta)": lambda c: c.startswith("D") and c[1:].isdigit(),
    "M (match)": lambda c: c.startswith("M") and c[1:].isdigit(),
    "V (Vesta)": lambda c: c.startswith("V") and c[1:].isdigit(),
    "id_* (identity)": lambda c: c.startswith("id_"),
}


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def profile_shape(df: pd.DataFrame, spec: DatasetSpec) -> None:
    section("Shape and contract")

    n, f = len(df), int(df[spec.target_column].sum())
    print(f"rows           {n:,}")
    print(f"columns        {df.shape[1]}")
    print(f"fraud          {f:,} ({f / n:.3%})  imbalance 1:{(n - f) / f:.0f}")

    duplicated = int(df.duplicated().sum())
    fraud_dupes = int(df.loc[df.duplicated(), spec.target_column].sum()) if duplicated else 0
    print(f"exact dupes    {duplicated:,}" + (f" ({fraud_dupes} fraud)" if duplicated else ""))
    print(
        f"  -> spec declares drop_exact_duplicates={spec.drop_exact_duplicates}: "
        + ("consistent" if bool(duplicated) or not spec.drop_exact_duplicates else "REVIEW")
    )

    time = df[spec.time_column]
    span_days = (time.max() - time.min()) / 86_400
    print(f"time span      {time.min():,.0f} -> {time.max():,.0f}  = {span_days:.1f} days")
    print(f"distinct times {time.nunique():,} across {n:,} rows")


def profile_missingness(df: pd.DataFrame) -> None:
    section("Missingness by column group")

    remaining = set(df.columns)
    for label, predicate in COLUMN_GROUPS.items():
        columns = [c for c in df.columns if predicate(c)]
        if not columns:
            continue
        remaining -= set(columns)
        ratio = df[columns].isna().mean()
        print(
            f"  {label:18s} {len(columns):>4d} cols   "
            f"NaN median {ratio.median():.1%}   max {ratio.max():.1%}   "
            f"fully-present {int((ratio == 0).sum())}"
        )

    others = sorted(remaining)
    ratio = df[others].isna().mean()
    print(f"  {'other':18s} {len(others):>4d} cols   NaN median {ratio.median():.1%}")

    heavy = ratio[ratio > 0.9]
    if len(heavy):
        print(f"\n  >90% missing among 'other': {sorted(heavy.index)[:8]}")


def entity_candidates(df: pd.DataFrame, spec: DatasetSpec) -> dict[str, pd.Series]:
    """Candidate stand-ins for a customer identifier."""
    available = set(df.columns)
    candidates: dict[str, pd.Series] = {}

    def part(column: str) -> pd.Series:
        """One component of a composite key, with absence made explicit.

        `astype(str)` keeps NaN as NaN, so without the fill a single missing
        component nulls the whole identifier — and `value_counts()` then drops
        those rows silently, understating both the group count and the singleton
        rate. `addr1` is absent for 11.4% of IEEE-CIS, so the distortion is not
        marginal.
        """
        return df[column].astype(str).fillna(ENTITY_MISSING)

    def key(*columns: str) -> pd.Series | None:
        if not set(columns) <= available:
            return None
        joined = part(columns[0])
        for column in columns[1:]:
            joined = joined + "_" + part(column)
        return joined

    for label, columns in [
        ("card1", ("card1",)),
        ("card1+addr1", ("card1", "addr1")),
        ("card1+card2+addr1", ("card1", "card2", "addr1")),
    ]:
        series = key(*columns)
        if series is not None:
            candidates[label] = series

    # The Kaggle "uid" trick: D1 counts days since a card-level event, so
    # (day - D1) is roughly constant per physical card and survives reissue of
    # the surrounding attributes.
    if {"card1", "addr1", "D1"} <= available:
        day = (df[spec.time_column] // 86_400).astype("float64")
        d1n = (day - df["D1"]).round().astype("Int64").astype(str)
        candidates["card1+addr1+D1n"] = (
            df["card1"].astype(str) + "_" + df["addr1"].astype(str) + "_" + d1n
        )
    return candidates


def profile_entities(df: pd.DataFrame, spec: DatasetSpec) -> None:
    section("Entity proxy candidates")

    if not spec.has_entity:
        print("spec declares entity_keys=None — this dataset carries no entity information.")
        return

    candidates = entity_candidates(df, spec)
    target = df[spec.target_column].to_numpy()
    n = len(df)

    print(
        f"  {'candidate':<22} {'groups':>8} {'txn/grp':>8} {'singleton':>10} "
        f"{'txn in grp>=5':>14} {'median hist':>12}"
    )
    print(f"  {'-' * 22} {'-' * 8} {'-' * 8} {'-' * 10} {'-' * 14} {'-' * 12}")

    for label, ids in candidates.items():
        counts = ids.value_counts()
        n_groups = len(counts)
        singleton = int((counts == 1).sum())
        in_big = int(counts[counts >= 5].sum())
        print(
            f"  {label:<22} {n_groups:>8,} {n / n_groups:>8.1f} "
            f"{singleton / n_groups:>9.1%} {in_big / n:>13.1%} {int(counts.median()):>12,}"
        )

    # Diagnostic only — see the module docstring on why this must not decide.
    print("\n  fraud concentration (diagnostic, NOT a selection criterion):")
    for label, ids in candidates.items():
        frame = pd.DataFrame({"g": ids, "y": target})
        per_group = frame.groupby("g")["y"].sum()
        multi = per_group[per_group > 1].sum()
        print(
            f"    {label:<22} {multi / target.sum():>6.1%} of fraud sits in groups "
            f"with more than one fraud case"
        )

    declared = "+".join(spec.entity_keys or [])
    print(f"\n  spec currently declares: {declared}")


def profile_drift(df: pd.DataFrame, spec: DatasetSpec, block_days: int = 30) -> None:
    section(f"Fraud rate over time ({block_days}-day blocks)")

    block = (df[spec.time_column] // (block_days * 86_400)).astype(int)
    grouped = df.groupby(block)[spec.target_column].agg(["size", "sum", "mean"])

    print(f"  {'block':>6} {'rows':>10} {'fraud':>8} {'rate':>8}")
    for index, row in grouped.iterrows():
        print(f"  {index:>6} {int(row['size']):>10,} {int(row['sum']):>8,} {row['mean']:>7.2%}")

    rates = grouped["mean"]
    print(f"\n  swing: {rates.min():.2%} -> {rates.max():.2%}  ({rates.max() / rates.min():.2f}x)")


def profile_folds(df: pd.DataFrame, spec: DatasetSpec) -> None:
    section("Fold arithmetic (what the split contract will produce)")

    n = len(df)
    n_holdout = int(n * spec.holdout_fraction)
    n_dev = n - n_holdout
    n_blocks = spec.n_cv_folds + 1
    per_block = n_dev // n_blocks
    rate = float(df[spec.target_column].mean())

    print(f"  holdout_fraction  {spec.holdout_fraction}")
    print(f"  n_cv_folds        {spec.n_cv_folds}  ({n_blocks} blocks)")
    print(f"  dev               ~{n_dev:,} rows")
    print(f"  per val block     ~{per_block:,} rows  ->  ~{int(per_block * rate):,} fraud")
    print(f"  holdout           ~{n_holdout:,} rows  ->  ~{int(n_holdout * rate):,} fraud")
    print(
        "\n  (uniform-rate estimate; the real counts come from build_splits.py, "
        "and will differ where the fraud rate drifts)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--block-days", type=int, default=30)
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    print(f"profiling {spec.name}")

    # No dedup and no strict contract check: the point is to *measure* what the
    # spec should declare, so the profiler must run on a spec that is still wrong.
    df, report = loader.load_raw(
        spec, drop_duplicates=False, strict=False, compute_hash=False
    )
    print(f"loaded {report.n_rows:,} rows x {report.n_columns} columns")

    profile_shape(df, spec)
    profile_missingness(df)
    profile_entities(df, spec)
    profile_drift(df, spec, args.block_days)
    profile_folds(df, spec)

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
