"""Protocol-level configuration — the constants that hold across datasets.

Anything that describes a *dataset* (column names, row counts, split fractions,
fold counts) lives in `src/datasets/`, not here. What remains is the research
protocol itself: the seed, the bootstrap settings, the alert budgets, and the
guard rails. Those are the same whether the run is on creditcard or IEEE-CIS,
and holding them in one place is what lets a result be traced to the settings
that produced it.

Nothing here should be overridden at a call site.
"""

from pathlib import Path

from src.datasets.spec import (
    DATASETS_DIR,
    EXPERIMENTS_ROOT,
    PROCESSED_ROOT,
    PROJECT_ROOT,
)

# --------------------------------------------------------------------------
# Paths (re-exported so callers have one import for "where things live")
# --------------------------------------------------------------------------

__all__ = [
    "BOOTSTRAP_ALPHA",
    "DATASETS_DIR",
    "EXPERIMENTS_ROOT",
    "MIN_DISTINCT_SCORE_RATIO",
    "N_BOOTSTRAP",
    "PRECISION_AT_K",
    "PRIMARY_METRIC",
    "PROCESSED_ROOT",
    "PROJECT_ROOT",
    "SEED",
]

_ = Path  # re-exported types are used by callers, not here

# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------

SEED = 42

# --------------------------------------------------------------------------
# Evaluation contract
# --------------------------------------------------------------------------

PRIMARY_METRIC = "auprc"

# Bootstrap resamples behind every reported confidence interval. An AUPRC point
# estimate on ~74 positives is not evidence; the interval is what makes it one.
N_BOOTSTRAP = 2_000
BOOTSTRAP_ALPHA = 0.05

# Alert budgets for precision@k — a human review queue is finite.
PRECISION_AT_K = (50, 100, 200, 500)

# --------------------------------------------------------------------------
# Guard rails
# --------------------------------------------------------------------------

# Below this ratio of distinct scores to rows, ranking metrics stop measuring
# the model and start measuring the tie-break. Chosen from a real failure: a
# LightGBM run with no L2 penalty produced 65 distinct scores across 45,397
# rows (0.0014) and its AUPRC fell to the random floor while ROC-AUC still read
# 0.80. A saturated model must be visible, not averaged into a table.
MIN_DISTINCT_SCORE_RATIO = 0.01
