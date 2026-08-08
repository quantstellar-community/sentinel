"""Run a registered model through the Phase 0 evaluation protocol.

    uv run python scripts/run_experiment.py --model xgboost
    uv run python scripts/run_experiment.py --all

Writes `experiments/results/<model>/record.json` and `scores.npz`. The scores
are what `scripts/compare_models.py` later pairs on, so a run is not complete
until they are saved.

The holdout stays untouched unless `--touch-holdout` is passed.
"""

from __future__ import annotations

import argparse
import sys

from src import config
from src.datasets import SPECS, get_spec
from src.evaluation import runner
from src.models import MODEL_REGISTRY, models_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--model", choices=sorted(MODEL_REGISTRY), help="registry name")
    parser.add_argument(
        "--all", action="store_true", help="run every model applicable to the dataset"
    )
    parser.add_argument("--n-bootstrap", type=int, default=config.N_BOOTSTRAP)
    parser.add_argument(
        "--touch-holdout",
        action="store_true",
        help="score the locked holdout. Once per phase, not per experiment.",
    )
    args = parser.parse_args(argv)

    if not args.model and not args.all:
        parser.error("pass --model <name> or --all")

    spec = get_spec(args.dataset)
    names = models_for(spec) if args.all else [args.model]
    records = [
        runner.run_and_report(
            name,
            spec=spec,
            n_bootstrap=args.n_bootstrap,
            touch_holdout=args.touch_holdout,
        )
        for name in names
    ]

    if len(records) > 1:
        print(f"\n{'=' * 72}\nsummary — {spec.name}\n{'=' * 72}")
        width = max(len(r.name) for r in records)
        for record in sorted(records, key=lambda r: -r.mean_auprc):
            print(
                f"  {record.name:<{width}}  mean AUPRC {record.mean_auprc:.4f}   "
                f"CI width {record.mean_ci_width:.4f}   "
                f"folds {[round(a, 3) for a in record.fold_auprcs]}"
            )
        print(
            "\nRanking by mean AUPRC alone proves nothing at these interval widths.\n"
            f"Run: uv run python scripts/compare_models.py --dataset {spec.name} "
            "<baseline> <challenger>"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
