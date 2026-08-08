"""The ULB / Worldline European credit-card dataset.

284,807 transactions over 48 hours, 492 of them fraud (0.17%). V1-V28 are
anonymised PCA components; only `Time` and `Amount` retain their original
meaning.

This dataset carries **no entity information at all** — no customer, merchant,
device, or card identifier. Behavioural features are therefore impossible on
it, which is not a gap in the pipeline but a property of the data.

`drop_exact_duplicates=True`: the raw file contains 1,081 fully duplicated
rows, 19 of them fraud. A duplicate landing in an evaluation block is scored
twice and inflates every metric; a duplicate pair straddling a split boundary
is outright leakage.

Four folds, chosen from the resulting fraud counts: 47-89 positives per
validation block and 74 in the holdout. That is thin — thin enough that the
AUPRC confidence interval runs about 0.23 wide — and it is the reason the
evaluation protocol reports intervals rather than point estimates.
"""

from __future__ import annotations

from src.datasets.spec import DATASETS_DIR, DatasetSpec

TIME_COLUMN = "Time"
AMOUNT_COLUMN = "Amount"
TARGET_COLUMN = "Class"
PCA_COLUMNS = [f"V{i}" for i in range(1, 29)]

FEATURE_COLUMNS = [TIME_COLUMN, *PCA_COLUMNS, AMOUNT_COLUMN]
EXPECTED_COLUMNS = [*FEATURE_COLUMNS, TARGET_COLUMN]

CREDITCARD = DatasetSpec(
    name="creditcard",
    raw_paths={"transaction": DATASETS_DIR / "creditcard.csv"},
    join_key=None,
    time_column=TIME_COLUMN,
    target_column=TARGET_COLUMN,
    amount_column=AMOUNT_COLUMN,
    entity_keys=None,
    categorical_columns=[],
    expected_rows=284_807,
    expected_fraud=492,
    drop_exact_duplicates=True,
    required_columns=EXPECTED_COLUMNS,
    expected_columns=EXPECTED_COLUMNS,
    holdout_fraction=0.20,
    n_cv_folds=4,
    # V1-V28 are already centred PCA components on comparable scales; Time and
    # Amount are raw and wildly out of range (Amount skew 16.98, max 25,691).
    # Measured on the development folds: scaling the V columns as well moves
    # logistic regression by +0.0036 mean AUPRC, significant on 1 of 4 folds —
    # i.e. nothing. The narrow default stands, and the `logreg_full_scale`
    # registry entry is what settled it.
    default_scale_columns=[TIME_COLUMN, AMOUNT_COLUMN],
)
