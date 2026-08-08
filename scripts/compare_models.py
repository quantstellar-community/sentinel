"""Paired comparison between two recorded runs.

    uv run python scripts/compare_models.py logreg xgboost

Loads the saved validation scores from both runs and bootstraps the AUPRC
*difference* fold by fold. This is the test that decides whether a model is
better; the ranking printed by `run_experiment.py --all` does not.

The two runs must have been scored on identical validation rows, which is
verified before anything is computed — pairing scores from different splits
would produce a confident, meaningless number.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from src import config
from src.datasets import SPECS, get_spec
from src.evaluation import metrics, runner


def compare(baseline: str, challenger: str, *, spec, n_bootstrap: int) -> dict:
    baseline_folds = runner.load_scores(baseline, spec)
    challenger_folds = runner.load_scores(challenger, spec)

    shared = sorted(set(baseline_folds) & set(challenger_folds))
    if not shared:
        raise SystemExit(f"no folds in common between {baseline!r} and {challenger!r}")

    baseline_record = runner.load_record(baseline, spec)
    challenger_record = runner.load_record(challenger, spec)
    if baseline_record["source_sha256"] != challenger_record["source_sha256"]:
        raise SystemExit("runs used different source data; rebuild splits and re-run both")

    print(f"[{spec.name}]  {baseline}  vs  {challenger}")
    print(f"folds {shared}   bootstrap {n_bootstrap}\n")

    comparisons = []
    for fold in shared:
        baseline_scores, baseline_y = baseline_folds[fold]
        challenger_scores, challenger_y = challenger_folds[fold]

        if not np.array_equal(baseline_y, challenger_y):
            raise SystemExit(
                f"fold {fold}: the two runs were scored on different rows. "
                "Both must come from the same split_manifest.json."
            )

        result = metrics.compare_auprc(
            baseline_y,
            baseline_scores,
            challenger_scores,
            label_a=baseline,
            label_b=challenger,
            n_bootstrap=n_bootstrap,
        )
        verdict = "SIGNIFICANT" if result.significant else "not significant"
        print(
            f"fold {fold}  ({int(baseline_y.sum())} positives)\n"
            f"  {baseline}: {result.auprc_a:.4f}   {challenger}: {result.auprc_b:.4f}\n"
            f"  delta {result.delta:+.4f}  "
            f"[{result.delta_ci_low:+.4f}, {result.delta_ci_high:+.4f}]  "
            f"P(better) {result.prob_b_better:.3f}   -> {verdict}\n"
        )
        comparisons.append({"fold": fold, **result.to_dict()})

    deltas = [c["delta"] for c in comparisons]
    n_significant_wins = sum(1 for c in comparisons if c["significant"] and c["delta"] > 0)
    n_significant_losses = sum(1 for c in comparisons if c["significant"] and c["delta"] < 0)

    print("=" * 72)
    print(f"mean delta across folds: {np.mean(deltas):+.4f}")
    print(
        f"{challenger} significantly better on {n_significant_wins}/{len(comparisons)} folds, "
        f"significantly worse on {n_significant_losses}/{len(comparisons)}"
    )
    if n_significant_wins == 0 and n_significant_losses == 0:
        print(
            f"\nVERDICT: no difference demonstrated. The data does not support a claim\n"
            f"that {challenger} beats {baseline} here, in either direction."
        )
    elif n_significant_wins and not n_significant_losses:
        print(f"\nVERDICT: {challenger} beats {baseline} on {n_significant_wins} of "
              f"{len(comparisons)} folds and loses on none.")
    elif n_significant_losses and not n_significant_wins:
        print(f"\nVERDICT: {challenger} is beaten by {baseline} on "
              f"{n_significant_losses} of {len(comparisons)} folds.")
    else:
        print(f"\nVERDICT: inconsistent — {challenger} wins {n_significant_wins} fold(s) "
              f"and loses {n_significant_losses}. Fold-to-fold variation dominates.")
    print("=" * 72)

    payload = {
        "dataset": spec.name,
        "baseline": baseline,
        "challenger": challenger,
        "n_bootstrap": n_bootstrap,
        "mean_delta": float(np.mean(deltas)),
        "n_folds": len(comparisons),
        "n_significant_wins": n_significant_wins,
        "n_significant_losses": n_significant_losses,
        "folds": comparisons,
    }

    out_dir = spec.results_dir / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{baseline}__vs__{challenger}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("baseline", help="registry name of the reference run")
    parser.add_argument("challenger", help="registry name of the run being tested")
    parser.add_argument("--n-bootstrap", type=int, default=config.N_BOOTSTRAP)
    args = parser.parse_args(argv)

    compare(
        args.baseline,
        args.challenger,
        spec=get_spec(args.dataset),
        n_bootstrap=args.n_bootstrap,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
