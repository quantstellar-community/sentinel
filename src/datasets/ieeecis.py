"""The IEEE-CIS / Vesta fraud dataset.

590,540 transactions over 182 days, 20,663 of them fraud (3.50%) — 42x more
positives and 91x more time than `creditcard.csv`. Two tables joined on
`TransactionID`.

**Only the training tables are usable.** `test_transaction.csv` carries no
`isFraud` column: it is the Kaggle competition test set and its labels are held
by the organisers. Pointing this spec at it would produce a frame that fails
validation, which is the correct outcome.

The fraud rate is not stationary — it moves 2.48% -> 4.04% -> 3.40% -> 4.18%
across successive 30-day blocks. That 1.6x swing is real drift, and it is the
first time this project has enough time span to measure any.

Six folds rather than four: roughly 2,360 positives per validation block and
4,130 in the holdout, against 47-89 and 74 on creditcard. The AUPRC confidence
interval should narrow by an order of magnitude.
"""

from __future__ import annotations

from dataclasses import replace

from src.datasets.spec import DATASETS_DIR, DatasetSpec

IEEE_DIR = DATASETS_DIR / "ieeecis-fraud-detection"

TIME_COLUMN = "TransactionDT"
AMOUNT_COLUMN = "TransactionAmt"
TARGET_COLUMN = "isFraud"
JOIN_KEY = "TransactionID"

#: Composite stand-in for a customer. This is a heuristic, not an identifier:
#: 37,280 groups, 15.8 transactions each on average, but 39.5% of groups hold a
#: single transaction. Reissued cards and changed addresses split one customer
#: across several groups. Any result built on behavioural features has to state
#: this assumption.
ENTITY_KEYS = ["card1", "card2", "addr1"]

CATEGORICAL_COLUMNS = [
    "ProductCD",
    "card4",
    "card6",
    "P_emaildomain",
    "R_emaildomain",
    *[f"M{i}" for i in range(1, 10)],
    "DeviceType",
    "DeviceInfo",
]

IEEECIS = DatasetSpec(
    name="ieeecis",
    raw_paths={
        "transaction": IEEE_DIR / "train_transaction.csv",
        "identity": IEEE_DIR / "train_identity.csv",
    },
    join_key=JOIN_KEY,
    time_column=TIME_COLUMN,
    target_column=TARGET_COLUMN,
    amount_column=AMOUNT_COLUMN,
    entity_keys=ENTITY_KEYS,
    categorical_columns=CATEGORICAL_COLUMNS,
    expected_rows=590_540,
    expected_fraud=20_663,
    # Left False deliberately: unlike creditcard, every row here carries a unique
    # TransactionID, and two rows identical across the feature columns can be a
    # legitimate pair of purchases. Whether to drop them is a question to be
    # measured (scripts/profile_dataset.py), not assumed.
    drop_exact_duplicates=False,
    # Only these must be present and non-null. The C/D/M/V blocks are sparse by
    # design — `id_*` is absent for most rows because identity data simply was
    # not collected, and that absence is itself a signal.
    required_columns=[JOIN_KEY, TIME_COLUMN, AMOUNT_COLUMN, TARGET_COLUMN],
    # No exact column-list contract: 435 columns after the join is data, not a
    # promise worth freezing.
    expected_columns=[],
    holdout_fraction=0.20,
    n_cv_folds=6,
    default_scale_columns=[TIME_COLUMN, AMOUNT_COLUMN],
    # `TransactionDT` is a second counter from an unstated reference point. The
    # offset does not matter — every behavioural window is a difference — but the
    # unit does, and this is the only dataset where those windows actually run.
    seconds_per_time_unit=1.0,
)


#: The same rows under a coarser customer proxy — `card1` alone.
#:
#: Declared as a second spec rather than a flag because that is what the entity
#: proxy *is*: layer 1 exists to hold everything that makes one dataset differ
#: from another, and `entity_keys` is the most consequential entry in it. The
#: side effect is exactly right — `processed_dir` and `results_dir` are
#: namespaced by `name`, so the two proxies cannot overwrite each other's splits
#: or records, and a paired comparison across them is impossible by construction.
#: (They are scored on the same rows but through different feature computations,
#: so pairing them would be comparing two pipelines, not two models.)
#:
#: ## Why this variant exists
#:
#: The measured conclusion that behavioural features add nothing on IEEE-CIS was
#: obtained under `card1+card2+addr1`, where only 91.9% of transactions sit in a
#: group with enough history to compute on. `card1` alone reaches 97.7%.
#:
#: The composite key is the more precise identifier when its parts are present,
#: but a reissued card changes `card2` and a house move changes `addr1`, and each
#: split shatters one real customer into several pseudo-entities with truncated
#: histories. If that fragmentation is what flattened the behavioural signal,
#: the null result is an artefact of the proxy rather than a fact about the
#: features — and this spec is how that gets measured instead of argued.
#:
#: The trade runs the other way too: 43.6 transactions per group suggests `card1`
#: merges several physical cards. Neither proxy is right; the point is to find
#: out whether the choice changes the answer.
IEEECIS_CARD1 = replace(
    IEEECIS,
    name="ieeecis_card1",
    entity_keys=["card1"],
)
