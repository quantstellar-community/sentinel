"""Phase 0 harness check — logistic regression across the expanding-window folds.

    uv run python scripts/baseline_sanity_check.py

Kept as a named entry point because `docs/evaluation_protocol.md` references it.
It delegates to the same code path as the general runner, so the two cannot
drift apart:

    uv run python scripts/run_experiment.py --model logreg

The purpose is not to score well. It is to confirm the harness produces sane
numbers end to end, and to establish the floor later models are measured against
with `scripts/compare_models.py`.
"""

from __future__ import annotations

import argparse
import sys

from src import config
from src.datasets import SPECS, get_spec
from src.evaluation import runner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--n-bootstrap", type=int, default=config.N_BOOTSTRAP)
    parser.add_argument(
        "--touch-holdout",
        action="store_true",
        help="score the locked holdout. Once per phase, not per experiment.",
    )
    args = parser.parse_args(argv)

    runner.run_and_report(
        "logreg",
        spec=get_spec(args.dataset),
        n_bootstrap=args.n_bootstrap,
        touch_holdout=args.touch_holdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
