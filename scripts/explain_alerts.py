"""Layer 10 — evidence for the alerts a model actually raises.

    uv run python scripts/explain_alerts.py --dataset ieeecis --model xgboost_behavioral

Takes the highest-risk rows of the last validation fold, attributes each score
to its features exactly, and asks what the smallest actionable change would have
been. Writes `explanations.json` beside the model's record.

The holdout is never touched here: an explanation is a property of a model, not
a measurement of it, so there is nothing to spend the locked split on.

Fold labels are read only to report whether an explained alert was right. They
reach nothing that fits.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from src.data import loader, splitter
from src.datasets import DEV_SPLIT_NAME, SPECS, get_spec
from src.evaluation import explain
from src.evaluation.runner import pipeline_for
from src.models import MODEL_REGISTRY, get_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--model", choices=sorted(MODEL_REGISTRY), default="xgboost")
    parser.add_argument("--top", type=int, default=5, help="alerts to explain")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    model = get_model(args.model, spec)
    if not model.explainable:
        raise SystemExit(
            f"{args.model} does not attribute its score. Layer 10 covers tree "
            f"ensembles; try --model xgboost."
        )

    dev = loader.load_split(DEV_SPLIT_NAME, spec)
    fold = splitter.expanding_window_folds(dev, spec)[-1]
    train, validation = dev.iloc[fold.train_idx], dev.iloc[fold.val_idx]

    pipeline = pipeline_for(model, spec).fit(train)
    X_train = pipeline.transform(train)
    columns = model.select_features(list(X_train.columns), spec)
    model.fit(X_train[columns], train[spec.target_column])

    X_validation = pipeline.transform(validation)[columns]
    scores = np.asarray(model.risk_score(X_validation))
    truth = validation[spec.target_column].to_numpy()

    ranked = np.argsort(-scores)[: args.top]
    print(f"\n{'=' * 72}\n{spec.name} / {args.model} — top {args.top} alerts, fold "
          f"{fold.index}\n{'=' * 72}")
    print(f"{len(validation):,} rows scored, {int(truth.sum()):,} fraud\n")

    payload = []
    explanations = explain.explain(model, X_validation.iloc[ranked])

    for rank, (position, explanation) in enumerate(zip(ranked, explanations, strict=True), 1):
        explanation.check_additivity()
        verdict = "FRAUD" if truth[position] else "legitimate"
        print(f"--- alert {rank}   score {explanation.risk_score:.4f}   "
              f"actually {verdict}")

        for attribution in explanation.top(3):
            value = "missing" if np.isnan(attribution.value) else f"{attribution.value:,.3f}"
            print(f"      {attribution.feature:<28} {value:>14}   "
                  f"contributes {attribution.contribution:+.3f}")

        result = explain.counterfactual(
            model, pipeline, validation, int(position),
            threshold=args.threshold, spec=spec,
        )
        if result.unreachable:
            print(f"      -> no {result.column} would clear {args.threshold}; this "
                  "alert does not turn on the amount")
        elif result.change == 0.0:
            print(f"      -> already below {args.threshold}")
        else:
            print(f"      -> {result.column} {result.original:,.2f} -> "
                  f"{result.proposed:,.2f} ({result.change:+,.2f}) would score "
                  f"{result.proposed_score:.4f}")

        payload.append(
            {
                "rank": rank,
                "actual_fraud": bool(truth[position]),
                **explanation.to_dict(),
                "counterfactual": result.to_dict(),
            }
        )

    directory = spec.results_dir / args.model
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "explanations.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {directory / 'explanations.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
