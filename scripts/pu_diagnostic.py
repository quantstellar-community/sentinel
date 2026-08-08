"""How much real fraud does the anomaly bootstrap actually find?

    uv run python scripts/pu_diagnostic.py --dataset ieeecis

`pu_cascade`'s AUPRC says how well the finished cascade ranks. It does not say
whether the pseudo-labels it learned from were any good, and those are two
different questions: a cascade can score respectably by learning a smooth
approximation of a teacher whose flags were mostly wrong.

This measures the teacher. For each fold it runs the bootstrap exactly as the
model does, then scores the manufactured labels against the truth.

**The labels are used for measurement only.** They are read after the bootstrap
has already run and are never passed to anything that fits. That separation is
the whole point of layer 5, and it is why this lives in a script rather than in
the model: a model that could reach these numbers would no longer be track C.

Sweeping `assumed_positive_rate` also exposes the circularity `history.md` §32
found in the design this replaces — the alert rate is an input, so the flagged
count is fixed before any data is seen. What varies with the data is only how
much real fraud lands inside it.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from src.data import loader, splitter
from src.datasets import DEV_SPLIT_NAME, SPECS, DatasetSpec, get_spec
from src.evaluation.runner import pipeline_for
from src.models.pu import PUCascade

RATES = [0.01, 0.03, 0.05, 0.10]


def bootstrap_quality(
    train: pd.DataFrame, spec: DatasetSpec, rate: float
) -> dict[str, float]:
    """Run the bootstrap on one training fold and score it against the truth."""
    model = PUCascade(assumed_positive_rate=rate).bind(spec)

    pipeline = pipeline_for(model, spec).fit(train)
    X = pipeline.transform(train)
    X = X[model.select_features(list(X.columns), spec)]

    # A constant zero target, exactly what the unlabeled regime hands the model.
    model.fit(X, pd.Series(0, index=X.index))

    flagged = model.pseudo_labels.astype(bool)
    truth = train[spec.target_column].to_numpy().astype(bool)

    n_flagged = int(flagged.sum())
    n_fraud = int(truth.sum())
    caught = int((flagged & truth).sum())

    return {
        "n_flagged": n_flagged,
        "precision": caught / n_flagged if n_flagged else float("nan"),
        "recall": caught / n_fraud if n_fraud else float("nan"),
        "lift": (caught / n_flagged) / (n_fraud / len(train)) if n_flagged else float("nan"),
        "prevalence": n_fraud / len(train),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--fold", type=int, default=None, help="default: the last fold")
    args = parser.parse_args(argv)

    spec = get_spec(args.dataset)
    dev = loader.load_split(DEV_SPLIT_NAME, spec)
    folds = splitter.expanding_window_folds(dev, spec)
    fold = folds[args.fold if args.fold is not None else -1]
    train = dev.iloc[fold.train_idx]

    print(f"\n{'=' * 72}\n{spec.name} — bootstrap quality, fold {fold.index}\n{'=' * 72}")
    print(f"training rows {len(train):,}   real fraud {int(train[spec.target_column].sum()):,} "
          f"({train[spec.target_column].mean():.2%})\n")
    print(f"{'assumed rate':>13}{'flagged':>10}{'precision':>11}{'recall':>9}{'lift':>8}")

    for rate in RATES:
        result = bootstrap_quality(train, spec, rate)
        print(f"{rate:>13.0%}{result['n_flagged']:>10,}{result['precision']:>11.3f}"
              f"{result['recall']:>9.3f}{result['lift']:>8.1f}x", flush=True)

    print(
        "\nThe flagged count is fixed by the assumed rate, not discovered. Only "
        "precision,\nrecall and lift carry information about the data."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
