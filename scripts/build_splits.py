"""Materialize a dataset's splits and write its manifest.

    uv run python scripts/build_splits.py --dataset creditcard
    uv run python scripts/build_splits.py --dataset ieeecis

Produces `datasets/processed/<dataset>/{dev,holdout}.parquet` and
`split_manifest.json`. Every split is checked for temporal leakage before it is
allowed to reach disk — a broken split cannot exist on the filesystem.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from src import __version__, config
from src.data import loader, splitter
from src.datasets import DEV_SPLIT_NAME, HOLDOUT_SPLIT_NAME, SPECS, DatasetSpec, get_spec


def build(
    spec: DatasetSpec,
    *,
    keep_duplicates: bool = False,
    skip_hash: bool = False,
) -> dict:
    print(f"dataset: {spec.name}")
    for table, path in spec.raw_paths.items():
        print(f"  reading {table}: {path}")

    df, report = loader.load_raw(
        spec,
        drop_duplicates=False if keep_duplicates else None,
        compute_hash=not skip_hash,
    )
    print(
        f"  {report.n_rows_raw:,} rows x {report.n_columns} cols"
        + (
            f" -> {report.n_rows:,} after dropping "
            f"{report.n_duplicates_dropped:,} exact duplicates "
            f"({report.n_fraud_duplicates_dropped} of them fraud)"
            if report.n_duplicates_dropped
            else " (no deduplication)"
        )
    )
    print(f"  {report.n_fraud:,} fraud remain ({report.fraud_rate:.5%})")

    dev, holdout, dev_cut = splitter.dev_holdout_split(df, spec)
    splitter.assert_no_temporal_leakage(dev, holdout, spec)

    dev_stats = splitter.describe(dev, DEV_SPLIT_NAME, spec)
    holdout_stats = splitter.describe(holdout, HOLDOUT_SPLIT_NAME, spec)

    print(f"\ndev/holdout cut at {spec.time_column}={dev_cut:,.0f}")
    for stats in (dev_stats, holdout_stats):
        print(
            f"  {stats.name:8s} n={stats.n_rows:>8,}  fraud={stats.n_fraud:>6,}  "
            f"rate={stats.fraud_rate:.5%}  t=[{stats.time_min:,.0f}, {stats.time_max:,.0f}]"
        )

    folds = splitter.expanding_window_folds(dev, spec)
    print(f"\n{len(folds)} expanding-window folds over dev:")
    for fold in folds:
        train, val = dev.iloc[fold.train_idx], dev.iloc[fold.val_idx]
        splitter.assert_no_temporal_leakage(train, val, spec)
        print(
            f"  fold {fold.index}  train n={fold.train_stats.n_rows:>8,} "
            f"fraud={fold.train_stats.n_fraud:>6,}   |   "
            f"val n={fold.val_stats.n_rows:>7,} fraud={fold.val_stats.n_fraud:>5,}"
        )

    fold_positives = [f.val_stats.n_fraud for f in folds]
    if min(fold_positives) < 20:
        print(
            f"\n  NOTE: smallest validation fold holds {min(fold_positives)} fraud cases. "
            "Per-fold AUPRC will be very noisy; read the aggregate, not the folds."
        )

    spec.processed_dir.mkdir(parents=True, exist_ok=True)
    dev.to_parquet(spec.split_path(DEV_SPLIT_NAME), index=False)
    holdout.to_parquet(spec.split_path(HOLDOUT_SPLIT_NAME), index=False)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sentinel_version": __version__,
        "dataset": spec.to_dict(),
        "config": {
            "seed": config.SEED,
            "keep_duplicates": keep_duplicates,
            "n_bootstrap": config.N_BOOTSTRAP,
        },
        "source": report.to_dict(),
        "dev_holdout_cut_time": dev_cut,
        "splits": {
            DEV_SPLIT_NAME: dev_stats.to_dict(),
            HOLDOUT_SPLIT_NAME: holdout_stats.to_dict(),
        },
        "folds": [fold.to_dict() for fold in folds],
    }
    spec.split_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nwrote {spec.split_path(DEV_SPLIT_NAME)}")
    print(f"wrote {spec.split_path(HOLDOUT_SPLIT_NAME)}")
    print(f"wrote {spec.split_manifest_path}")
    print(
        f"\nholdout is locked: {holdout_stats.n_fraud:,} fraud cases, "
        "to be scored once at the end of a phase."
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument(
        "--all", action="store_true", help="build splits for every registered dataset"
    )
    parser.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="keep exact-duplicate rows regardless of what the spec declares",
    )
    parser.add_argument(
        "--skip-hash",
        action="store_true",
        help="skip source SHA-256, which takes a few seconds on a large file",
    )
    args = parser.parse_args(argv)

    specs = [get_spec(n) for n in sorted(SPECS)] if args.all else [get_spec(args.dataset)]
    for index, spec in enumerate(specs):
        if index:
            print(f"\n{'=' * 72}\n")
        build(spec, keep_duplicates=args.keep_duplicates, skip_hash=args.skip_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())
