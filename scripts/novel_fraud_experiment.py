"""Does the anomaly layer catch fraud the supervised model was never taught?

    uv run python scripts/novel_fraud_experiment.py

`scripts/run_experiment.py` cannot answer this. Its benchmark draws validation
fraud from the same distribution the supervised model trained on, so it rewards
exactly the thing supervised learning is already good at and measures nothing
about the claim in the README — that modelling normality first buys robustness
to fraud that has never been labelled.

The design here creates that situation deliberately:

1.  Partition the dev-set fraud into `k` behavioural clusters (KMeans over the
    PCA components). These stand in for "fraud types".
2.  For each cluster `c`, relabel every fraud in `c` as legitimate in the
    *training* fold. The supervised model is now blind to that type, and — as in
    reality — the anomaly model's "normal" training data is contaminated with
    the undiscovered fraud.
3.  Evaluate on the validation fold restricted to legitimate rows plus cluster
    `c` fraud only, so the score measures performance on the unseen type alone.
4.  Compare against an oracle run that did see cluster `c` labels. The gap is
    the cost of novelty for each approach.

The prediction under test: the supervised model degrades sharply between oracle
and blind, and the anomaly model — which never used labels — does not.

**A design caveat, stated because it matters.** The cluster taxonomy is fitted
on all dev fraud, which uses labels the blinded models are not allowed to see.
That is legitimate because the clustering defines the *experiment*, not any
model's inputs: it decides which labels get hidden and which rows are scored.
No model receives cluster identity. It does mean the fraud "types" are defined
with hindsight, so they are cleanly separated by construction — a real novel
fraud type would be messier.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src import config
from src.data import loader, splitter
from src.data.preprocessor import Preprocessor
from src.datasets import DEV_SPLIT_NAME, SPECS, DatasetSpec, get_spec
from src.evaluation import metrics
from src.models import get_model

DEFAULT_CLUSTERS = 4
SUPERVISED_MODEL = "xgboost"
ANOMALY_MODEL = "isolation_forest"

#: The hybrid is here because "is the anomaly layer more robust?" and "does the
#: anomaly layer make a supervised system more robust?" are different questions,
#: and only the second one decides whether to build it into the pipeline. The
#: iforest-only hybrid is used rather than the full one so a fit stays seconds
#: rather than a minute per cell.
HYBRID_MODEL = "xgboost_hybrid_iforest"

MODELS = (SUPERVISED_MODEL, ANOMALY_MODEL, HYBRID_MODEL)


@dataclass
class CellResult:
    """One (cluster, fold, model, condition) measurement."""

    cluster: int
    fold: int
    model: str
    condition: str  # "oracle" | "blind"
    n_eval: int
    n_positive: int
    auprc: float
    roc_auc: float
    precision_at_100: float

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def behavioural_columns(dev: pd.DataFrame, spec: DatasetSpec) -> list[str]:
    """Numeric columns usable for clustering fraud into behavioural types."""
    excluded = {spec.target_column, spec.time_column, spec.join_key}
    return [
        c
        for c in dev.columns
        if c not in excluded and pd.api.types.is_numeric_dtype(dev[c])
    ]


def cluster_fraud(dev: pd.DataFrame, k: int, spec: DatasetSpec | str | None = None) -> pd.Series:
    """Assign each dev fraud row a cluster id; legitimate rows get -1."""
    spec = get_spec(spec)
    fraud_mask = dev[spec.target_column] == 1
    fraud = dev.loc[fraud_mask, behavioural_columns(dev, spec)].fillna(0.0)

    # Standardise so no single PCA component dominates the distance.
    centred = (fraud - fraud.mean()) / fraud.std(ddof=0).replace(0, 1.0)

    kmeans = KMeans(n_clusters=k, n_init=10, random_state=config.SEED)
    labels = kmeans.fit_predict(centred)

    assignment = pd.Series(-1, index=dev.index, dtype=int)
    assignment.loc[fraud_mask] = labels
    return assignment


def fit_and_score(
    model_name: str,
    train: pd.DataFrame,
    evaluate_on: pd.DataFrame,
    spec: DatasetSpec,
):
    """Same preprocessing and label discipline the runner applies."""
    model = get_model(model_name, spec)

    X_train, y_train = loader.split_xy(train, spec)
    X_eval, _ = loader.split_xy(evaluate_on, spec)

    columns = model.select_features(list(X_train.columns), spec)
    X_train, X_eval = X_train[columns], X_eval[columns]

    scale_columns = model.resolve_scale_columns(columns, spec)
    if scale_columns:
        pre = Preprocessor(columns=scale_columns).fit(X_train)
        X_train, X_eval = pre.transform(X_train), pre.transform(X_eval)

    if model.trains_on_normal_only:
        normal = y_train == 0
        X_train, y_train = X_train[normal], y_train[normal]

    model.fit(X_train, y_train)
    return np.asarray(model.risk_score(X_eval), dtype=float)


def run(k: int, n_bootstrap: int, spec: DatasetSpec) -> dict:
    dev = loader.load_split(DEV_SPLIT_NAME, spec)
    assignment = cluster_fraud(dev, k, spec)

    sizes = assignment[assignment >= 0].value_counts().sort_index()
    print(f"fraud taxonomy: {k} clusters over {int(sizes.sum())} dev fraud cases")
    for cluster, size in sizes.items():
        print(f"  cluster {cluster}: {size} cases")

    folds = splitter.expanding_window_folds(dev, spec)
    results: list[CellResult] = []

    for cluster in sizes.index:
        print(f"\n{'=' * 72}\ncluster {cluster}  ({sizes[cluster]} fraud cases)\n{'=' * 72}")

        for fold in folds:
            train = dev.iloc[fold.train_idx]
            val = dev.iloc[fold.val_idx]
            splitter.assert_no_temporal_leakage(train, val, spec)

            train_clusters = assignment.iloc[fold.train_idx]
            val_clusters = assignment.iloc[fold.val_idx]

            # Evaluate on legitimate rows plus this cluster's fraud only.
            keep = (val_clusters == -1) | (val_clusters == cluster)
            val_subset = val[keep.to_numpy()]
            y_eval = val_subset[spec.target_column].to_numpy()

            if y_eval.sum() < 5:
                print(f"  fold {fold.index}: only {int(y_eval.sum())} cases, skipped")
                continue

            # Blind: this cluster's fraud is relabelled legitimate in training.
            blind_train = train.copy()
            hide = (train_clusters == cluster).to_numpy()
            blind_train.loc[blind_train.index[hide], spec.target_column] = 0

            for model_name in MODELS:
                for condition, training_data in (("oracle", train), ("blind", blind_train)):
                    scores = fit_and_score(model_name, training_data, val_subset, spec)
                    result = metrics.evaluate(
                        y_eval, scores, n_bootstrap=n_bootstrap, seed=config.SEED
                    )
                    results.append(
                        CellResult(
                            cluster=int(cluster),
                            fold=fold.index,
                            model=model_name,
                            condition=condition,
                            n_eval=len(y_eval),
                            n_positive=int(y_eval.sum()),
                            auprc=result.auprc,
                            roc_auc=result.roc_auc,
                            precision_at_100=result.precision_at_k.get(100, float("nan")),
                        )
                    )

            row = {
                (r.model, r.condition): r.auprc
                for r in results
                if r.fold == fold.index and r.cluster == cluster
            }
            print(f"  fold {fold.index}  ({int(y_eval.sum())} cases of this type)")
            for model_name in MODELS:
                oracle = row[(model_name, "oracle")]
                blind = row[(model_name, "blind")]
                print(
                    f"      {model_name:<24} oracle {oracle:.4f} -> blind {blind:.4f} "
                    f"({blind - oracle:+.4f})"
                )

    return summarize(results, k, n_bootstrap, spec)


def summarize(results: list[CellResult], k: int, n_bootstrap: int, spec: DatasetSpec) -> dict:
    frame = pd.DataFrame([r.to_dict() for r in results])
    if frame.empty:
        raise SystemExit("no cluster/fold combination had enough cases to evaluate")

    print(f"\n{'=' * 72}\nsummary\n{'=' * 72}")

    table = frame.pivot_table(
        index="model", columns="condition", values="auprc", aggfunc="mean"
    )
    table["cost_of_novelty"] = table["oracle"] - table["blind"]
    table["retained"] = table["blind"] / table["oracle"]

    print("\nmean AUPRC across all clusters and folds:\n")
    print(f"  {'model':<20} {'oracle':>8} {'blind':>8} {'drop':>8} {'retained':>9}")
    for model_name, row in table.iterrows():
        print(
            f"  {model_name:<20} {row['oracle']:>8.4f} {row['blind']:>8.4f} "
            f"{row['cost_of_novelty']:>8.4f} {row['retained']:>8.1%}"
        )

    supervised = table.loc[SUPERVISED_MODEL]
    anomaly = table.loc[ANOMALY_MODEL]
    hybrid = table.loc[HYBRID_MODEL] if HYBRID_MODEL in table.index else None

    print(
        f"\nRobustness — share of its own oracle score each keeps when the fraud\n"
        f"type is unseen: {SUPERVISED_MODEL} {supervised['retained']:.1%}, "
        f"{ANOMALY_MODEL} {anomaly['retained']:.1%}."
    )
    if anomaly["retained"] > supervised["retained"]:
        print(
            "  -> The anomaly layer degrades less, which is the property the README\n"
            "     claims for it and the one the standard benchmark cannot show."
        )
    else:
        print(
            f"  -> The anomaly layer is NOT more robust than {SUPERVISED_MODEL} here.\n"
            "     Reported as measured; see the hindsight caveat in the docstring."
        )

    # Robustness is not the same as usefulness. State the absolute levels too,
    # because a model can degrade less simply by starting far lower.
    print(
        f"\nAbsolute level on unseen types: {SUPERVISED_MODEL} {supervised['blind']:.4f} "
        f"vs {ANOMALY_MODEL} {anomaly['blind']:.4f}."
    )
    if supervised["blind"] > anomaly["blind"]:
        print(
            f"  -> Degrading less is not the same as scoring better. Even blinded,\n"
            f"     {SUPERVISED_MODEL} outranks the anomaly layer on the unseen type; the\n"
            "     anomaly layer is stable because it was never very good here, not\n"
            "     because it recognises the novel fraud."
        )

    if hybrid is not None:
        print(
            f"\nThe question that decides the pipeline — does the anomaly signal make\n"
            f"the supervised model more robust?\n"
            f"  {SUPERVISED_MODEL:<24} blind {supervised['blind']:.4f}  "
            f"(retains {supervised['retained']:.1%})\n"
            f"  {HYBRID_MODEL:<24} blind {hybrid['blind']:.4f}  "
            f"(retains {hybrid['retained']:.1%})"
        )
        gain = hybrid["blind"] - supervised["blind"]
        if gain > 0:
            print(
                f"  -> The hybrid recovers {gain:+.4f} AUPRC on fraud types it was never\n"
                "     taught. This is the case for the anomaly layer that the\n"
                "     same-distribution benchmark could not make."
            )
        else:
            print(
                f"  -> The hybrid recovers nothing ({gain:+.4f}). On this data the anomaly\n"
                "     signal does not help the supervised model handle novel fraud\n"
                "     either, which is a stronger negative result than the\n"
                "     same-distribution benchmark alone could support."
            )

    # Where the supervised model actually collapses, per cluster.
    per_cluster = frame[frame.model == SUPERVISED_MODEL].pivot_table(
        index="cluster", columns="condition", values="auprc", aggfunc="mean"
    )
    per_cluster["drop"] = per_cluster["oracle"] - per_cluster["blind"]
    print(f"\n{SUPERVISED_MODEL} cost of novelty per cluster:")
    for cluster, row in per_cluster.iterrows():
        print(
            f"  cluster {cluster}: {row['oracle']:.4f} -> {row['blind']:.4f} "
            f"(drop {row['drop']:+.4f})"
        )

    payload = {
        "dataset": spec.name,
        "n_clusters": k,
        "n_bootstrap": n_bootstrap,
        "supervised_model": SUPERVISED_MODEL,
        "anomaly_model": ANOMALY_MODEL,
        "summary": {
            model_name: {
                "oracle": float(row["oracle"]),
                "blind": float(row["blind"]),
                "cost_of_novelty": float(row["cost_of_novelty"]),
                "retained": float(row["retained"]),
            }
            for model_name, row in table.iterrows()
        },
        "cells": [r.to_dict() for r in results],
    }

    out_dir = spec.results_dir / "novel_fraud"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"k{k}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(SPECS), default=None)
    parser.add_argument("--clusters", type=int, default=DEFAULT_CLUSTERS)
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=0,
        help="0 by default: this experiment reads the oracle-to-blind gap, "
        "not the interval on any single cell",
    )
    args = parser.parse_args(argv)

    run(args.clusters, args.n_bootstrap, get_spec(args.dataset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
