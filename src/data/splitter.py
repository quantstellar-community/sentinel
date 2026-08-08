"""Layer 3 — Temporal Partition.

Every training row must precede every evaluation row, and a final holdout is
locked away. This is the layer that protects the first architectural invariant,
and the one easiest to get subtly wrong.

Two things make it more than a call to `train_test_split`:

1.  Cuts land on the *value* of the time column, never on row position. Many
    rows share a timestamp — creditcard has 284,807 rows across 124,592 distinct
    times — so a positional cut would split a tie group across the boundary.
2.  Model selection uses an expanding window over several folds. A single
    holdout leaves too few positives for a point estimate to mean anything.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src.datasets import DatasetSpec, get_spec


class SplitError(ValueError):
    """Raised when a requested split would be degenerate or unsafe."""


@dataclass(frozen=True)
class SplitStats:
    """Shape of one side of a split. Written verbatim into the manifest."""

    name: str
    n_rows: int
    n_fraud: int
    fraud_rate: float
    time_min: float
    time_max: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Fold:
    """One expanding-window fold: train up to `cut`, validate after."""

    index: int
    cut_time: float
    train_idx: np.ndarray
    val_idx: np.ndarray
    train_stats: SplitStats
    val_stats: SplitStats

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "cut_time": self.cut_time,
            "train": self.train_stats.to_dict(),
            "val": self.val_stats.to_dict(),
        }


def describe(df: pd.DataFrame, name: str, spec: DatasetSpec | str | None = None) -> SplitStats:
    """Summarize a split for the manifest."""
    spec = get_spec(spec)
    target = df[spec.target_column]
    return SplitStats(
        name=name,
        n_rows=len(df),
        n_fraud=int(target.sum()),
        fraud_rate=float(target.mean()) if len(df) else 0.0,
        time_min=float(df[spec.time_column].min()) if len(df) else float("nan"),
        time_max=float(df[spec.time_column].max()) if len(df) else float("nan"),
    )


def find_cut_time(times: pd.Series, fraction: float) -> float:
    """Smallest observed timestamp `t` such that `times <= t` covers `fraction`.

    Snapping to an observed value is what keeps tied rows together: `times <= t`
    necessarily takes every row recorded at `t`. The cost is that the realized
    fraction drifts slightly from the requested one, which is the right trade.
    """
    if not 0.0 < fraction < 1.0:
        raise SplitError(f"fraction must be in (0, 1), got {fraction}")

    ordered = np.sort(times.to_numpy())
    target_position = int(np.ceil(fraction * len(ordered))) - 1
    target_position = min(max(target_position, 0), len(ordered) - 1)
    cut = float(ordered[target_position])

    if cut == ordered[-1]:
        raise SplitError(
            f"fraction={fraction} lands on the final timestamp ({cut}); "
            "the right-hand side of the split would be empty"
        )
    return cut


def temporal_split(
    df: pd.DataFrame, fraction: float, spec: DatasetSpec | str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Cut into (before, after) at the timestamp covering `fraction` of rows."""
    spec = get_spec(spec)
    time_column = spec.time_column

    cut = find_cut_time(df[time_column], fraction)
    before = df[df[time_column] <= cut]
    after = df[df[time_column] > cut]

    if before.empty or after.empty:
        raise SplitError(f"degenerate split at cut={cut}: {len(before)} / {len(after)} rows")

    return before, after, cut


def dev_holdout_split(
    df: pd.DataFrame,
    spec: DatasetSpec | str | None = None,
    holdout_fraction: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Separate the locked holdout from the development set.

    The holdout is scored once per phase. Everything else — features,
    hyperparameters, thresholds — is decided on the development folds.
    """
    spec = get_spec(spec)
    fraction = spec.holdout_fraction if holdout_fraction is None else holdout_fraction
    return temporal_split(df, 1.0 - fraction, spec)


def _block_cuts(
    df: pd.DataFrame, spec: DatasetSpec, n_folds: int
) -> tuple[list[float], pd.Series]:
    """The `n_folds` timestamps dividing the frame into `n_folds + 1` blocks."""
    if n_folds < 1:
        raise SplitError(f"n_folds must be >= 1, got {n_folds}")

    n_blocks = n_folds + 1
    times = df[spec.time_column]

    cuts: list[float] = []
    for block in range(1, n_blocks):
        cut = find_cut_time(times, block / n_blocks)
        if cuts and cut <= cuts[-1]:
            raise SplitError(
                f"n_folds={n_folds} produces non-monotonic cuts on this data "
                f"(cut {cut} <= previous {cuts[-1]}); use fewer folds"
            )
        cuts.append(cut)
    return cuts, times


def _build_folds(
    df: pd.DataFrame,
    spec: DatasetSpec,
    cuts: list[float],
    times: pd.Series,
    train_blocks: int | None,
) -> list[Fold]:
    """Assemble folds from block boundaries.

    `train_blocks=None` keeps every earlier block (expanding). An integer keeps
    only that many of the most recent ones (sliding). The **validation block is
    identical either way** — that is deliberate and load-bearing: two runs that
    differ only in their training window are then scored on exactly the same
    rows, so layer 8 can pair them.
    """
    positions = np.arange(len(df))
    folds: list[Fold] = []

    for index, cut in enumerate(cuts):
        next_cut = cuts[index + 1] if index + 1 < len(cuts) else float("inf")

        above = times > float("-inf")
        if train_blocks is not None and index - train_blocks >= 0:
            # Block `index + 1 - train_blocks` begins just after this boundary.
            above = times > cuts[index - train_blocks]

        train_mask = (above & (times <= cut)).to_numpy()
        val_mask = ((times > cut) & (times <= next_cut)).to_numpy()

        train_df = df[train_mask]
        val_df = df[val_mask]
        if val_df.empty:
            raise SplitError(f"fold {index} has an empty validation block")
        if train_df.empty:
            raise SplitError(
                f"fold {index} has an empty training window; train_blocks="
                f"{train_blocks} is too narrow for this partition"
            )

        folds.append(
            Fold(
                index=index,
                cut_time=cut,
                train_idx=positions[train_mask],
                val_idx=positions[val_mask],
                train_stats=describe(train_df, f"fold{index}_train", spec),
                val_stats=describe(val_df, f"fold{index}_val", spec),
            )
        )
    return folds


def expanding_window_folds(
    df: pd.DataFrame,
    spec: DatasetSpec | str | None = None,
    n_folds: int | None = None,
) -> list[Fold]:
    """Build expanding-window folds over the development set.

    Divided into `n_folds + 1` equal-row blocks; fold `i` trains on blocks
    `0..i` and validates on block `i+1`, so every fold trains only on the past
    and validates on the immediate future.

    This is the protocol every recorded experiment uses. `sliding_window_folds`
    exists alongside it as a measurement, not as a replacement.
    """
    spec = get_spec(spec)
    n_folds = spec.n_cv_folds if n_folds is None else n_folds
    cuts, times = _block_cuts(df, spec, n_folds)
    return _build_folds(df, spec, cuts, times, train_blocks=None)


def sliding_window_folds(
    df: pd.DataFrame,
    spec: DatasetSpec | str | None = None,
    n_folds: int | None = None,
    train_blocks: int = 1,
) -> list[Fold]:
    """Folds that keep the training window a fixed width and let it move.

    Fold `i` trains on the `train_blocks` most recent blocks ending at block `i`,
    discarding everything older, and validates on block `i+1`.

    ## Why this exists

    An expanding window grows as it advances, so a model retrained under it has
    both *fresher* and *more* data than one frozen at the start. The measured
    benefit of retraining therefore confounds two effects, and on IEEE-CIS that
    ambiguity is not academic: retraining is worth +28% at the last block while
    the frozen model itself decays only 9%, which suggests most of the gain is
    volume rather than recency — but suggests is not measures.

    Holding the window width fixed separates them. Against a frozen model
    trained on the same number of blocks, the only remaining difference is
    *when* those blocks are from:

        frozen    train block 0        score block i+1   same width, oldest
        sliding   train block i        score block i+1   same width, newest
        expanding train blocks 0..i    score block i+1   widest

    `sliding - frozen` is recency with volume held constant; `expanding -
    sliding` is what accumulating history adds on top.

    ## Not a change of protocol

    Early folds have less history than `train_blocks` asks for and fall back to
    everything available, which makes fold 0 identical across both schemes — a
    free check that the two partitions really are the same partition.
    """
    spec = get_spec(spec)
    n_folds = spec.n_cv_folds if n_folds is None else n_folds
    if train_blocks < 1:
        raise SplitError(f"train_blocks must be >= 1, got {train_blocks}")

    cuts, times = _block_cuts(df, spec, n_folds)
    return _build_folds(df, spec, cuts, times, train_blocks=train_blocks)


def assert_no_temporal_leakage(
    train: pd.DataFrame, test: pd.DataFrame, spec: DatasetSpec | str | None = None
) -> None:
    """Fail if any test row is contemporaneous with or older than a train row.

    Runs on every split before anything reaches disk, so a broken split cannot
    exist on the filesystem.
    """
    spec = get_spec(spec)
    if train.empty or test.empty:
        raise SplitError("cannot check leakage on an empty split")

    train_max = float(train[spec.time_column].max())
    test_min = float(test[spec.time_column].min())
    if train_max >= test_min:
        raise SplitError(
            f"temporal leakage: train ends at {train_max} but test begins at "
            f"{test_min} (overlapping timestamps must not straddle a cut)"
        )
