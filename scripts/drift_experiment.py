"""Layer 9 — how fast a frozen model decays, and what retraining is worth.

    uv run python scripts/drift_experiment.py --dataset ieeecis --model xgboost

Fits once on the first block of the development set and scores every later
block. Pairs that frozen arm against the retrained arm already recorded by
`run_experiment.py`, which is what an expanding window produces by construction.

Answers PIPELINE_V2 experiments #9 and #10:

* **#9** — the decay curve itself: AUPRC against distance in blocks.
* **#10** — real temporal drift rather than an artificial novel-fraud design.
  Training on the first month and evaluating on the last is the honest version
  of the same question, and IEEE-CIS is the first dataset here with the span to
  ask it.

Requires the retrained arm to exist first, so the two are paired on identical
validation rows rather than recomputed.
"""

from __future__ import annotations

import argparse
import json
import sys

from src import config
from src.datasets import SPECS, get_spec
from src.evaluation import drift, runner
from src.models import MODEL_REGISTRY, get_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--model", choices=sorted(MODEL_REGISTRY), default="xgboost")
    parser.add_argument("--n-bootstrap", type=int, default=config.N_BOOTSTRAP)
    parser.add_argument(
        "--train-blocks",
        type=int,
        default=1,
        help="width of the sliding window, in blocks. 1 matches the frozen arm, "
        "which is what holds volume constant.",
    )
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    get_model(args.model, spec)  # fails fast if the model cannot run here

    record = runner.load_record(args.model, spec)
    retrained = record["fold_auprcs"]

    print(f"\n{'=' * 72}\n{spec.name} / {args.model} — decay from a frozen model\n{'=' * 72}")
    curve = drift.decay_curve(
        MODEL_REGISTRY[args.model], spec=spec, n_bootstrap=args.n_bootstrap
    )
    print(f"trained once on {curve.n_train:,} rows "
          f"({curve.n_train_fraud:,} fraud), then never updated\n")

    drift.assert_baseline_agrees(curve.auprcs[0], retrained[0])
    gains = curve.retraining_gain(retrained)

    print("--- fitting the sliding arm (fixed-width window, moving forward)\n")
    sliding = drift.sliding_curve(
        MODEL_REGISTRY[args.model],
        spec=spec,
        n_bootstrap=args.n_bootstrap,
        train_blocks=args.train_blocks,
    )
    drift.assert_baseline_agrees(sliding.auprcs[0], curve.auprcs[0])
    parts = drift.decompose(curve.auprcs, sliding.auprcs, retrained)

    print(f"{'block':>6}{'frozen':>9}{'sliding':>9}{'expanding':>11}"
          f"{'recency':>9}{'volume':>9}{'total':>9}{'train rows':>12}")
    for i, point in enumerate(curve.points):
        print(f"{point.block:>6}{curve.auprcs[i]:>9.4f}{sliding.auprcs[i]:>9.4f}"
              f"{retrained[i]:>11.4f}{parts['recency'][i]:>+9.4f}"
              f"{parts['volume'][i]:>+9.4f}{parts['total'][i]:>+9.4f}"
              f"{sliding.points[i].n_train:>12,}")

    first, last = curve.auprcs[0], curve.auprcs[-1]
    print(f"\nfrozen model: {first:.4f} at block 1 -> {last:.4f} at block "
          f"{curve.points[-1].block}   ({(last - first) / first:+.1%})")
    print(f"mean value of retraining: {sum(gains) / len(gains):+.4f} AUPRC")

    later = slice(1, None)  # block 1 is identical across all three arms
    mean_recency = sum(parts["recency"][later]) / (len(parts["recency"]) - 1)
    mean_volume = sum(parts["volume"][later]) / (len(parts["volume"]) - 1)
    total = mean_recency + mean_volume
    print(f"\ndecomposition over blocks 2..{curve.points[-1].block}:")
    print(f"  recency (fresher data, same width) {mean_recency:>+8.4f}"
          f"   {mean_recency / total:>6.0%}")
    print(f"  volume  (more history on top)      {mean_volume:>+8.4f}"
          f"   {mean_volume / total:>6.0%}")
    print(
        "\nThe two sum to the retraining gain by construction. They imply opposite\n"
        "policies: recency says discard stale data, volume says accumulate it."
    )

    directory = spec.results_dir / args.model
    directory.mkdir(parents=True, exist_ok=True)

    # Invariant IV: the arms' raw scores have to outlive this run, or the paired
    # test below could never be repeated without recomputing — which is exactly
    # what the invariant forbids.
    print(f"\nwrote {drift.save_scores(curve, sliding, directory)}")

    print(f"\n--- paired bootstrap on the decomposition ({args.n_bootstrap} draws)")
    print("Point estimates say which way each effect leans; this says whether the")
    print("lean survives resampling. Both are measured on the same rows.\n")

    paired = drift.paired_decomposition(
        curve, sliding, runner.load_scores(args.model, spec), n_bootstrap=args.n_bootstrap
    )
    print(f"{'block':>6}   {'recency (sliding - frozen)':<34}"
          f"{'volume (expanding - sliding)':<34}")
    significant = {"recency": 0, "volume": 0}
    for entry in paired[1:]:  # block 1 is identical across arms by construction
        cells = []
        for effect in ("recency", "volume"):
            comparison = entry[effect]
            mark = "*" if comparison.significant else " "
            significant[effect] += int(comparison.significant)
            cells.append(
                f"{comparison.delta:+.4f} [{comparison.delta_ci_low:+.4f},"
                f"{comparison.delta_ci_high:+.4f}]{mark}"
            )
        print(f"{entry['block']:>6}   {cells[0]:<34}{cells[1]:<34}")

    n_blocks = len(paired) - 1
    print(f"\n  recency significant on {significant['recency']}/{n_blocks} blocks")
    print(f"  volume  significant on {significant['volume']}/{n_blocks} blocks")
    payload_paired = [
        {
            "block": e["block"],
            "recency": e["recency"].to_dict(),
            "volume": e["volume"].to_dict(),
        }
        for e in paired
    ]
    payload = {
        **curve.to_dict(),
        "retrained_auprcs": retrained,
        "retraining_gain": gains,
        "sliding": sliding.to_dict(),
        "train_blocks": args.train_blocks,
        "decomposition": parts,
        "paired_decomposition": payload_paired,
    }
    (directory / "decay.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {directory / 'decay.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
