"""Layer 9 — Drift Protocol: how fast does a model stop being worth its weight?

Fraud is adversarial. A model that stands still loses value because the people
it blocks read the block and change what they do. That much is assumed
everywhere in the literature; *how fast* is a measurement, and IEEE-CIS is the
first dataset in this project with enough time span to take it — 182 days
against creditcard's two, with the fraud rate itself moving 2.48% -> 4.04% ->
3.40% -> 4.18% across successive 30-day blocks.

## Two measurements, one run

PIPELINE_V2 §11 asks for a decay curve and, separately, for frozen-versus-
retrained. The second does not need its own experiment:

    frozen[i]     train on block 0,      score block i+1   <- measured here
    retrained[i]  train on blocks 0..i,  score block i+1   <- already in the record

`run_cv` has been producing the retrained arm all along; it is what an expanding
window *is*. So one pass over the frozen arm, paired against the existing
record, yields both the decay curve and the value of retraining at each
boundary.

Two consequences worth stating:

* `frozen[0]` and `retrained[0]` train on identical rows, so they must agree
  exactly. That is a free correctness check on the whole construction, and
  `assert_baseline_agrees` enforces it rather than trusting it.
* The two arms are scored on the *same* validation rows, so the difference is
  paired in the sense layer 8 requires and can be bootstrapped directly.

## What this cannot separate

An expanding window grows its training set as it advances, so `retrained[i]`
differs from `frozen[i]` in two ways at once: it has seen more recent data and
it has seen *more* data. A gain therefore does not decompose into "recency" and
"volume" without a sliding-window arm holding volume fixed — the third
measurement in §11, and a layer-3 change rather than a layer-9 one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.data import loader, splitter
from src.datasets import DEV_SPLIT_NAME, DatasetSpec, get_spec
from src.evaluation import metrics
from src.evaluation.runner import _fit_and_score, pipeline_for


class DriftError(RuntimeError):
    """Raised when a decay measurement cannot be made honestly."""


@dataclass
class DecayPoint:
    """One block scored by a model frozen at the start of the development set."""

    block: int
    #: Blocks between the end of training and this evaluation block. The x-axis.
    distance: int
    n: int
    n_positive: int
    result: metrics.EvaluationResult
    scores: np.ndarray = field(repr=False)
    y: np.ndarray = field(repr=False)
    #: Rows the model was trained on. Constant under a sliding window, growing
    #: under an expanding one — which is the whole distinction being measured.
    n_train: int = 0

    def to_dict(self) -> dict:
        return {
            "block": self.block,
            "distance": self.distance,
            "n": self.n,
            "n_positive": self.n_positive,
            "n_train": self.n_train,
            **self.result.to_dict(),
        }


@dataclass
class DecayCurve:
    """A frozen model's performance against time, plus what retraining bought."""

    dataset: str
    model: str
    n_train: int
    n_train_fraud: int
    points: list[DecayPoint] = field(repr=False)

    @property
    def auprcs(self) -> list[float]:
        return [point.result.auprc for point in self.points]

    def retraining_gain(self, retrained_auprcs: list[float]) -> list[float]:
        """`retrained[i] - frozen[i]` per block: the value of retraining.

        The caller supplies the retrained arm from an existing experiment record
        rather than recomputing it, for the reason invariant IV gives: a
        recomputed number carries every library and seed difference the pairing
        exists to remove.
        """
        if len(retrained_auprcs) != len(self.points):
            raise DriftError(
                f"the retrained arm has {len(retrained_auprcs)} folds but the "
                f"decay curve has {len(self.points)} blocks; they are not the "
                "same partition and cannot be paired"
            )
        return [
            retrained - frozen
            for retrained, frozen in zip(retrained_auprcs, self.auprcs, strict=True)
        ]

    def to_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "model": self.model,
            "n_train": self.n_train,
            "n_train_fraud": self.n_train_fraud,
            "points": [point.to_dict() for point in self.points],
        }


def assert_baseline_agrees(frozen: float, retrained: float, tolerance: float = 1e-9) -> None:
    """The first block trains on identical rows in both arms, so it must match.

    A mismatch means the two arms are not the partition they claim to be, and
    every later difference would be measuring that discrepancy rather than
    drift.
    """
    if abs(frozen - retrained) > tolerance:
        raise DriftError(
            f"block 1 disagrees between the arms: frozen {frozen:.6f} vs "
            f"retrained {retrained:.6f}. Both train on block 0 alone, so this is "
            "a construction error rather than a drift signal."
        )


def decay_curve(
    model_factory,
    *,
    spec: DatasetSpec | str | None = None,
    dev: pd.DataFrame | None = None,
    n_bootstrap: int | None = None,
) -> DecayCurve:
    """Fit once on the first block, then score every later block.

    The training set is deliberately the *smallest* one any fold uses. That is
    the point: it isolates ageing from accumulation, since the model never sees
    another row after the start.
    """
    spec = get_spec(spec)
    if dev is None:
        dev = loader.load_split(DEV_SPLIT_NAME, spec)
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap

    folds = splitter.expanding_window_folds(dev, spec)
    train = dev.iloc[folds[0].train_idx]

    points: list[DecayPoint] = []
    for fold in folds:
        evaluation_block = dev.iloc[fold.val_idx]
        splitter.assert_no_temporal_leakage(train, evaluation_block, spec)

        model = model_factory().bind(spec)
        scores, y, _, _, _, _ = _fit_and_score(
            model, train, evaluation_block, spec, pipeline_for(model, spec)
        )
        result = metrics.evaluate(y, scores, n_bootstrap=n_bootstrap, seed=config.SEED)

        points.append(
            DecayPoint(
                block=fold.index + 1,
                distance=fold.index + 1,
                n=len(evaluation_block),
                n_positive=int(y.sum()),
                result=result,
                scores=scores,
                y=y,
                n_train=len(train),
            )
        )

    return DecayCurve(
        dataset=spec.name,
        model=model_factory().name,
        n_train=len(train),
        n_train_fraud=int(train[spec.target_column].sum()),
        points=points,
    )


def sliding_curve(
    model_factory,
    *,
    spec: DatasetSpec | str | None = None,
    dev: pd.DataFrame | None = None,
    n_bootstrap: int | None = None,
    train_blocks: int = 1,
) -> DecayCurve:
    """Refit on a fixed-width window that moves forward, and score the next block.

    The third arm, and the one that turns the retraining gain from a single
    number into a decomposition. It holds the amount of training data constant
    while letting its age vary, so what it measures against a frozen model of
    the same width is recency alone.
    """
    spec = get_spec(spec)
    if dev is None:
        dev = loader.load_split(DEV_SPLIT_NAME, spec)
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap

    folds = splitter.sliding_window_folds(dev, spec, train_blocks=train_blocks)
    points: list[DecayPoint] = []

    for fold in folds:
        train, evaluation_block = dev.iloc[fold.train_idx], dev.iloc[fold.val_idx]
        splitter.assert_no_temporal_leakage(train, evaluation_block, spec)

        model = model_factory().bind(spec)
        scores, y, _, _, _, _ = _fit_and_score(
            model, train, evaluation_block, spec, pipeline_for(model, spec)
        )
        result = metrics.evaluate(y, scores, n_bootstrap=n_bootstrap, seed=config.SEED)

        points.append(
            DecayPoint(
                block=fold.index + 1,
                distance=1,  # a sliding window is always one block behind
                n=len(evaluation_block),
                n_positive=int(y.sum()),
                result=result,
                scores=scores,
                y=y,
                n_train=len(train),
            )
        )

    first = dev.iloc[folds[0].train_idx]
    return DecayCurve(
        dataset=spec.name,
        model=model_factory().name,
        n_train=len(first),
        n_train_fraud=int(first[spec.target_column].sum()),
        points=points,
    )


def save_scores(frozen: DecayCurve, sliding: DecayCurve, directory) -> Path:
    """Persist both arms' raw per-block scores.

    Invariant IV: a fold's scores have to outlive the run that produced them. An
    earlier version of this layer saved only the AUPRCs, which left the
    decomposition impossible to test — a paired bootstrap needs the scores
    themselves, and recomputing them later is explicitly *not* equivalent
    because it drags in every library and seed difference the pairing exists to
    remove.

    The expanding arm is not written here: `run_cv` already saved it under
    `scores.npz`, and storing a second copy would invite the two drifting apart.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    arrays: dict[str, np.ndarray] = {}
    for label, curve in (("frozen", frozen), ("sliding", sliding)):
        for point in curve.points:
            arrays[f"{label}_block{point.block}_scores"] = point.scores
            arrays[f"{label}_block{point.block}_y"] = point.y

    path = directory / "decay_scores.npz"
    np.savez_compressed(path, **arrays)
    return path


def paired_decomposition(
    frozen: DecayCurve,
    sliding: DecayCurve,
    expanding_scores: dict[int, tuple[np.ndarray, np.ndarray]],
    *,
    n_bootstrap: int | None = None,
    seed: int | None = None,
) -> list[dict]:
    """Bootstrap the recency and volume differences per block, paired.

    The point estimates in `decompose` say which way each effect leans; this
    says whether the lean survives resampling. Both differences are measured on
    the *same* rows, which is what makes the pairing legitimate and the interval
    narrow enough to be worth reading.

    Refuses to proceed unless all three arms carry identical labels for a block.
    Two arms scored on different rows would still produce a confident number.
    """
    n_bootstrap = config.N_BOOTSTRAP if n_bootstrap is None else n_bootstrap
    seed = config.SEED if seed is None else seed

    results: list[dict] = []
    for index, (frozen_point, sliding_point) in enumerate(
        zip(frozen.points, sliding.points, strict=True)
    ):
        if index not in expanding_scores:
            raise DriftError(
                f"the expanding arm has no fold {index}; it was produced by a "
                "different partition and cannot be paired against"
            )
        expanding_score, expanding_y = expanding_scores[index]

        if not (
            np.array_equal(frozen_point.y, sliding_point.y)
            and np.array_equal(frozen_point.y, expanding_y)
        ):
            raise DriftError(
                f"block {frozen_point.block}: the three arms were scored on "
                "different rows. A decomposition across them would be confident "
                "and meaningless."
            )

        recency = metrics.compare_auprc(
            frozen_point.y,
            frozen_point.scores,
            sliding_point.scores,
            label_a="frozen",
            label_b="sliding",
            n_bootstrap=n_bootstrap,
            seed=seed,
        )
        volume = metrics.compare_auprc(
            frozen_point.y,
            sliding_point.scores,
            expanding_score,
            label_a="sliding",
            label_b="expanding",
            n_bootstrap=n_bootstrap,
            seed=seed,
        )
        results.append(
            {"block": frozen_point.block, "recency": recency, "volume": volume}
        )
    return results


def decompose(
    frozen: list[float], sliding: list[float], expanding: list[float]
) -> dict[str, list[float]]:
    """Split the retraining gain into recency and volume.

        recency = sliding  - frozen     same window width, newer data
        volume  = expanding - sliding   same recency, more history
        total   = expanding - frozen    what an expanding retrain is worth

    The two parts sum to the total by construction, which is the point: the
    single number the decay experiment produced said retraining helps without
    saying why, and the two answers imply opposite operational policies —
    discard stale data, or accumulate it.
    """
    if not len(frozen) == len(sliding) == len(expanding):
        raise DriftError(
            f"arms have {len(frozen)}, {len(sliding)} and {len(expanding)} blocks; "
            "they are not the same partition and cannot be decomposed"
        )
    return {
        "recency": [s - f for s, f in zip(sliding, frozen, strict=True)],
        "volume": [e - s for e, s in zip(expanding, sliding, strict=True)],
        "total": [e - f for e, f in zip(expanding, frozen, strict=True)],
    }


__all__ = [
    "DecayCurve",
    "DecayPoint",
    "DriftError",
    "assert_baseline_agrees",
    "decay_curve",
    "decompose",
    "paired_decomposition",
    "save_scores",
    "sliding_curve",
]
