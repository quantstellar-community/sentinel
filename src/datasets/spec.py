"""Layer 1 — Domain Adapter.

Everything that makes one dataset differ from another, declared as *data*
rather than as code. No layer below this one imports a schema constant
directly; they all read it off the spec they were handed.

The test for whether this boundary is intact: adding a third dataset should
mean adding one `DatasetSpec` (and, if it brings new structure, one
`FeatureGroup`) — and touching nothing in the model, execution, or evaluation
layers. If a change to those layers becomes necessary, the boundary has been
violated somewhere and the cause is worth finding.

Corollary: never branch on `spec.name` below this layer. Wanting to write
`if spec.name == "ieeecis"` means the spec is missing a declaration; add the
field instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = PROJECT_ROOT / "datasets"
PROCESSED_ROOT = DATASETS_DIR / "processed"
EXPERIMENTS_ROOT = PROJECT_ROOT / "experiments" / "results"

DEV_SPLIT_NAME = "dev"
HOLDOUT_SPLIT_NAME = "holdout"

#: Stands in for a missing component of a composite entity key. Reserved rather
#: than borrowed from the data: no card number or address code renders as "?".
ENTITY_MISSING = "?"


class DatasetError(ValueError):
    """Raised when a spec is internally inconsistent."""


@dataclass(frozen=True)
class DatasetSpec:
    """The declaration of a dataset. Immutable, passed down by parameter."""

    name: str

    # --- Where the data lives -------------------------------------------
    #: Logical table name -> path. The first entry is the primary table.
    raw_paths: dict[str, Path]
    #: Column to LEFT JOIN secondary tables onto the primary one. None if single-table.
    join_key: str | None

    # --- Column roles ----------------------------------------------------
    time_column: str
    target_column: str
    amount_column: str
    #: Columns whose combination stands in for a customer. None when the dataset
    #: carries no entity information at all — the single most consequential
    #: switch in the system, since it decides whether behavioural features,
    #: entity-aware label regimes, and per-entity drift are available.
    entity_keys: list[str] | None
    categorical_columns: list[str] = field(default_factory=list)

    # --- Data contract, checked at load ----------------------------------
    expected_rows: int = 0
    expected_fraud: int = 0
    drop_exact_duplicates: bool = False
    #: Columns that must be present and non-null. Empty means "check them all",
    #: which is right for a small clean file and wrong for one with 400 sparse
    #: columns.
    required_columns: list[str] = field(default_factory=list)
    #: When set, the loader checks column names and order exactly. Left empty for
    #: wide datasets where the column list is data, not contract.
    expected_columns: list[str] = field(default_factory=list)

    # --- Split contract ---------------------------------------------------
    holdout_fraction: float = 0.20
    #: Chosen from the fraud count per validation block, not by habit. More folds
    #: thins both ends: fewer positives to evaluate on, less history for fold 0.
    n_cv_folds: int = 4

    # --- Default preprocessing -------------------------------------------
    #: Columns a scale-sensitive model rescales by default. Models may override.
    default_scale_columns: list[str] = field(default_factory=list)

    # --- Explanation ------------------------------------------------------
    #: Raw columns a counterfactual may propose changing. Everything absent from
    #: this list is immutable, which is the conservative default and the right
    #: one: "be ten years younger" or "have signed up through another channel"
    #: are not recommendations. Empty means the amount column alone, the only
    #: field on either dataset that a person could actually act on — the rest of
    #: IEEE-CIS is anonymised and creditcard's V1-V28 are PCA components with no
    #: interpretation to act on at all.
    counterfactual_columns: list[str] = field(default_factory=list)

    # --- Time semantics ---------------------------------------------------
    #: How many seconds one unit of `time_column` represents. Behavioural
    #: windows are stated in real time ("24H", "30D") and have to be converted
    #: into the column's own units to mean anything. Both current datasets count
    #: seconds, so this is 1.0 for both — declared rather than assumed, because a
    #: dataset in milliseconds would otherwise produce windows a thousand times
    #: too short and no error at all.
    seconds_per_time_unit: float = 1.0

    def __post_init__(self) -> None:
        if self.join_key is None and len(self.raw_paths) > 1:
            raise DatasetError(
                f"{self.name}: {len(self.raw_paths)} tables declared but no join_key"
            )
        if self.entity_keys is not None and not self.entity_keys:
            raise DatasetError(
                f"{self.name}: entity_keys=[] is ambiguous; use None for "
                "'this dataset has no entity information'"
            )
        if not 0.0 < self.holdout_fraction < 1.0:
            raise DatasetError(f"{self.name}: holdout_fraction must be in (0, 1)")
        if self.n_cv_folds < 1:
            raise DatasetError(f"{self.name}: n_cv_folds must be >= 1")
        if self.seconds_per_time_unit <= 0:
            raise DatasetError(f"{self.name}: seconds_per_time_unit must be > 0")

    # --- Derived ----------------------------------------------------------

    @property
    def has_entity(self) -> bool:
        """Whether behavioural, per-entity features are possible at all."""
        return bool(self.entity_keys)

    @property
    def mutable_columns(self) -> list[str]:
        """Raw columns a counterfactual may move. Defaults to the amount alone."""
        return list(self.counterfactual_columns) or [self.amount_column]

    @property
    def primary_table(self) -> str:
        return next(iter(self.raw_paths))

    @property
    def primary_path(self) -> Path:
        return self.raw_paths[self.primary_table]

    @property
    def processed_dir(self) -> Path:
        """Where materialized splits live. Namespaced so datasets cannot collide."""
        return PROCESSED_ROOT / self.name

    @property
    def split_manifest_path(self) -> Path:
        return self.processed_dir / "split_manifest.json"

    @property
    def results_dir(self) -> Path:
        """Namespaced results.

        Two runs of the same model name on different datasets must never be
        paired against each other; keeping them in separate trees makes that
        mistake hard to make by accident.
        """
        return EXPERIMENTS_ROOT / self.name

    def split_path(self, split_name: str) -> Path:
        return self.processed_dir / f"{split_name}.parquet"

    def entity_id(self, df) -> "object":
        """A single Series identifying the entity of each row.

        Composite keys are joined into one string. Callers must check
        `has_entity` first — asking an entity-free dataset for this is a
        programming error, not a runtime condition.

        A missing component becomes `ENTITY_MISSING` rather than propagating
        null. Two reasons, and the first is a bug this cost real time to find:
        `Series.astype(str)` keeps NaN as NaN, so joining the parts made the
        whole identifier null for any row missing any component. On IEEE-CIS
        that is 60,417 rows — `addr1` alone is absent for 11.4% — and they
        collapsed into one "entity" with 60,416 transactions of history. Nothing
        raised; the behavioural columns simply described a bucket rather than a
        customer.

        The second reason is that filling is also the right answer. `card1` is
        never missing, so a row with no `addr1` still carries most of the
        identifying information, and grouping it with the other rows of the same
        card is more accurate than discarding it. This mirrors `MISSING_CODE` in
        the categorical encoder: absence is a distinguishable state, not a null.
        """
        if not self.entity_keys:
            raise DatasetError(f"{self.name} declares no entity_keys")

        keys = [df[k].astype(str).fillna(ENTITY_MISSING) for k in self.entity_keys]
        joined = keys[0]
        for key in keys[1:]:
            joined = joined + "_" + key
        return joined

    def to_dict(self) -> dict:
        """The subset that belongs in an experiment record."""
        return {
            "name": self.name,
            "time_column": self.time_column,
            "target_column": self.target_column,
            "amount_column": self.amount_column,
            "entity_keys": list(self.entity_keys) if self.entity_keys else None,
            "expected_rows": self.expected_rows,
            "expected_fraud": self.expected_fraud,
            "drop_exact_duplicates": self.drop_exact_duplicates,
            "holdout_fraction": self.holdout_fraction,
            "n_cv_folds": self.n_cv_folds,
        }
