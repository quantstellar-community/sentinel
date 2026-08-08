"""How much history is worth keeping? Sweep the sliding window's width.

    uv run python scripts/window_sweep.py --dataset ieeecis --model xgboost

`drift_experiment.py` measures the *decomposition* — how much of the retraining
gain is recency and how much is volume — and for that the window has to be
exactly one block wide, matching the frozen arm so volume is held constant.

That answers a scientific question and leaves an operational one open. Knowing
recency dominates does not say how much history to keep: the two points already
measured are the extremes (1 block and everything), and the shape between them
is what a deployment actually has to choose from.

This sweeps that interval. If two or three blocks already capture most of the
benefit, that is the operating point — not either extreme.

Pairs every width against the widest arm on identical rows, so the reported
differences are differences rather than two unrelated measurements.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from src import config
from src.data import loader, splitter
from src.datasets import DEV_SPLIT_NAME, SPECS, get_spec
from src.evaluation import drift, metrics, runner
from src.models import MODEL_REGISTRY, get_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--model", choices=sorted(MODEL_REGISTRY), default="xgboost")
    parser.add_argument(
        "--widths",
        type=int,
        nargs="+",
        default=None,
        help="window widths in blocks. Default: every width up to n_folds - 1.",
    )
    parser.add_argument("--n-bootstrap", type=int, default=config.N_BOOTSTRAP)
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    get_model(args.model, spec)  # fails fast if the model cannot run here
    widths = args.widths or list(range(1, spec.n_cv_folds))

    # The expanding arm is the reference: it keeps everything, so it is the
    # ceiling each narrower window is spending less data to approach.
    record = runner.load_record(args.model, spec)
    expanding = record["fold_auprcs"]
    expanding_scores = runner.load_scores(args.model, spec)

    print(f"\n{'=' * 72}\n{spec.name} / {args.model} — sliding window width sweep"
          f"\n{'=' * 72}")
    print(f"reference: expanding window, mean AUPRC {np.mean(expanding):.4f}\n")

    curves: dict[int, drift.DecayCurve] = {}
    for width in widths:
        print(f"--- fitting width={width} block(s)", flush=True)
        curves[width] = drift.sliding_curve(
            MODEL_REGISTRY[args.model],
            spec=spec,
            n_bootstrap=args.n_bootstrap,
            train_blocks=width,
        )

    print(f"\n{'width':>6}{'mean AUPRC':>12}{'vs expanding':>14}"
          f"{'train rows':>12}{'% of expanding data':>21}")
    dev = loader.load_split(DEV_SPLIT_NAME, spec)
    expanding_rows = len(splitter.expanding_window_folds(dev, spec)[-1].train_idx)
    rows: list[dict] = []
    for width in widths:
        curve = curves[width]
        mean = float(np.mean(curve.auprcs))
        last_rows = curve.points[-1].n_train
        share = last_rows / expanding_rows
        print(f"{width:>6}{mean:>12.4f}{mean - np.mean(expanding):>+14.4f}"
              f"{last_rows:>12,}{share:>20.0%}")
        rows.append(
            {
                "train_blocks": width,
                "mean_auprc": mean,
                "delta_vs_expanding": mean - float(np.mean(expanding)),
                "train_rows_last_fold": last_rows,
                "share_of_expanding_data": share,
                "per_block_auprc": curve.auprcs,
            }
        )

    # Per-block paired tests against the expanding arm on the final block, where
    # the widths differ most: at block 1 every arm has the same data by
    # construction, so a difference there would be a bug, not a finding.
    print(f"\n--- paired against expanding on the last block "
          f"({args.n_bootstrap} draws)\n")
    last_index = len(expanding) - 1
    expanding_score, expanding_y = expanding_scores[last_index]

    print(f"{'width':>6}   {'delta vs expanding':<34}")
    for width in widths:
        point = curves[width].points[last_index]
        if not np.array_equal(point.y, expanding_y):
            raise SystemExit(
                f"width {width}: arms scored on different rows; not comparable"
            )
        comparison = metrics.compare_auprc(
            expanding_y,
            expanding_score,
            point.scores,
            label_a="expanding",
            label_b=f"sliding{width}",
            n_bootstrap=args.n_bootstrap,
            seed=config.SEED,
        )
        mark = "*" if comparison.significant else " "
        print(f"{width:>6}   {comparison.delta:+.4f} "
              f"[{comparison.delta_ci_low:+.4f},{comparison.delta_ci_high:+.4f}]{mark}")
        rows[widths.index(width)]["paired_vs_expanding_last_block"] = comparison.to_dict()

    print("\n* = interval excludes zero. A width whose interval covers zero is")
    print("  statistically indistinguishable from keeping all the history.")

    directory = spec.results_dir / args.model
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "window_sweep.json"
    path.write_text(
        json.dumps(
            {"model": args.model, "dataset": spec.name,
             "expanding_auprcs": expanding, "widths": rows},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
