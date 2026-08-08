"""Prove the refactor changed no behaviour.

    uv run python scripts/verify_migration.py

Compares freshly-written records against a snapshot taken before the layer
refactor, and fails on any numerical difference.

This is the only test that distinguishes "refactoring" from "rewriting". A
layer boundary can be moved without changing a single result; if a result does
move, something about the computation changed too, and that has to be found
before anything is built on top of it.

Usage:

    # before refactoring
    cp -r experiments/results experiments/results_pre_refactor

    # after refactoring, re-run the models, then
    uv run python scripts/verify_migration.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.datasets import EXPERIMENTS_ROOT, SPECS, get_spec

DEFAULT_GOLDEN = EXPERIMENTS_ROOT.parent / "results_pre_refactor"

#: Per-fold AUPRC is compared to this many decimal places. Bootstrap intervals
#: are excluded from the comparison: they depend on a seeded RNG whose call
#: sequence legitimately shifts when code is reorganised. The point estimate
#: must not move at all.
TOLERANCE = 1e-9


def load_records(directory: Path) -> dict[str, dict]:
    return {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*/record.json"))
    }


def compare(golden_dir: Path, current_dir: Path) -> tuple[int, int, list[str]]:
    golden = load_records(golden_dir)
    current = load_records(current_dir)

    if not golden:
        raise SystemExit(
            f"no golden records under {golden_dir}. Snapshot before refactoring:\n"
            f"  cp -r {current_dir} {golden_dir}"
        )

    problems: list[str] = []
    checked = matched = 0

    missing = sorted(set(golden) - set(current))
    if missing:
        problems.append(
            f"{len(missing)} model(s) present in the snapshot but not re-run: "
            f"{', '.join(missing)}"
        )

    for name in sorted(set(golden) & set(current)):
        checked += 1
        before, after = golden[name], current[name]

        old_folds = before["fold_auprcs"]
        new_folds = after["fold_auprcs"]

        if len(old_folds) != len(new_folds):
            problems.append(
                f"{name}: fold count changed {len(old_folds)} -> {len(new_folds)}"
            )
            continue

        deltas = [abs(a - b) for a, b in zip(old_folds, new_folds, strict=True)]
        worst = max(deltas) if deltas else 0.0

        if worst > TOLERANCE:
            problems.append(
                f"{name}: per-fold AUPRC moved by up to {worst:.2e}\n"
                f"    before {[round(v, 6) for v in old_folds]}\n"
                f"    after  {[round(v, 6) for v in new_folds]}"
            )
            continue

        mean_delta = abs(before["mean_auprc"] - after["mean_auprc"])
        if mean_delta > TOLERANCE:
            problems.append(
                f"{name}: mean AUPRC moved by {mean_delta:.2e} "
                f"({before['mean_auprc']:.6f} -> {after['mean_auprc']:.6f})"
            )
            continue

        matched += 1
        print(f"  OK    {name:28s} mean {after['mean_auprc']:.6f}  ({len(new_folds)} folds)")

    return checked, matched, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN,
        help="snapshot directory taken before the refactor",
    )
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    print(f"golden : {args.golden}")
    print(f"current: {spec.results_dir}\n")

    checked, matched, problems = compare(args.golden, spec.results_dir)

    print()
    if problems:
        print("=" * 72)
        print(f"MIGRATION CHECK FAILED — {len(problems)} problem(s)")
        print("=" * 72)
        for problem in problems:
            print(f"\n  {problem}")
        print(
            "\nA refactor that moves a number is not a refactor. Find the cause "
            "before building on top of this."
        )
        return 1

    print("=" * 72)
    print(f"MIGRATION CHECK PASSED — {matched}/{checked} models reproduce exactly")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
