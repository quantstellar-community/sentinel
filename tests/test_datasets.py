"""Layer 1 contract tests.

The boundary this layer defends: nothing below it may assume a particular
dataset. These tests check the declarations themselves and the derived paths
that keep two datasets from colliding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import (
    CREDITCARD,
    IEEECIS,
    IEEECIS_CARD1,
    SPECS,
    DatasetError,
    DatasetSpec,
    get_spec,
)


def test_registry_holds_every_declared_dataset():
    assert set(SPECS) == {"creditcard", "ieeecis", "ieeecis_card1"}


def test_the_card1_variant_differs_only_in_its_entity_proxy():
    """Two proxies over the same rows, declared as two specs because that is
    what layer 1 is for. Everything else must match, or a comparison between
    them would be measuring more than the proxy."""
    assert IEEECIS_CARD1.entity_keys == ["card1"]
    assert IEEECIS.entity_keys == ["card1", "card2", "addr1"]

    for field in ("raw_paths", "time_column", "target_column", "amount_column",
                  "expected_rows", "expected_fraud", "n_cv_folds",
                  "holdout_fraction"):
        assert getattr(IEEECIS_CARD1, field) == getattr(IEEECIS, field), field


def test_the_variant_cannot_overwrite_the_originals_artifacts():
    """Namespacing by `name` is what keeps the two proxies' splits and records
    apart. Without it the second run would silently overwrite the first."""
    assert IEEECIS_CARD1.processed_dir != IEEECIS.processed_dir
    assert IEEECIS_CARD1.results_dir != IEEECIS.results_dir


def test_get_spec_resolves_by_name_and_passes_specs_through():
    assert get_spec("creditcard") is CREDITCARD
    assert get_spec(IEEECIS) is IEEECIS
    assert get_spec(None) is CREDITCARD  # documented default


def test_unknown_dataset_lists_the_options():
    with pytest.raises(KeyError, match="unknown dataset"):
        get_spec("does_not_exist")


# --------------------------------------------------------------------------
# The entity switch — the single most consequential declaration
# --------------------------------------------------------------------------


def test_entity_declaration_is_explicit():
    """`None` means "no entity information exists", which is not the same as
    "an empty list of keys" — the second would be a silent bug."""
    assert CREDITCARD.entity_keys is None
    assert CREDITCARD.has_entity is False

    assert IEEECIS.entity_keys == ["card1", "card2", "addr1"]
    assert IEEECIS.has_entity is True


def test_empty_entity_keys_is_rejected_as_ambiguous():
    with pytest.raises(DatasetError, match="ambiguous"):
        DatasetSpec(
            name="bad",
            raw_paths={"t": CREDITCARD.primary_path},
            join_key=None,
            time_column="Time",
            target_column="Class",
            amount_column="Amount",
            entity_keys=[],
        )


def test_entity_id_joins_a_composite_key():
    frame = pd.DataFrame({"card1": [1, 2], "card2": [10, 20], "addr1": [100, 200]})
    ids = IEEECIS.entity_id(frame)

    assert list(ids) == ["1_10_100", "2_20_200"]
    assert ids.nunique() == 2


def test_entity_id_on_an_entity_free_dataset_is_a_programming_error():
    with pytest.raises(DatasetError, match="no entity_keys"):
        CREDITCARD.entity_id(pd.DataFrame({"x": [1]}))


def test_entity_id_survives_a_missing_component():
    """`Series.astype(str)` keeps NaN as NaN, so joining the parts of a
    composite key used to null the whole identifier whenever any one of them was
    absent. On IEEE-CIS that silently pooled 60,417 rows — `addr1` alone is
    missing for 11.4% — into a single entity carrying 60,416 transactions of
    "history". Nothing raised and every behavioural column described that bucket
    instead of a customer.
    """
    frame = pd.DataFrame(
        {"card1": [1, 1, 2], "card2": [10.0, 10.0, 20.0], "addr1": [100.0, np.nan, np.nan]}
    )
    ids = IEEECIS.entity_id(frame)

    assert ids.isna().sum() == 0, "a missing component must not null the identifier"
    assert ids.iloc[1] != ids.iloc[2], (
        "rows missing the same component still belong to different cards"
    )
    assert ids.iloc[0] != ids.iloc[1], "absence is a distinguishable state, not a wildcard"


def test_entity_id_keeps_rows_of_one_card_together_when_the_address_is_absent():
    """The reason absence is filled rather than treated as unknown: `card1` is
    never missing, so a row without `addr1` still carries most of the
    identifying information and belongs with the rest of its card."""
    frame = pd.DataFrame(
        {"card1": [7, 7], "card2": [10.0, 10.0], "addr1": [np.nan, np.nan]}
    )

    assert IEEECIS.entity_id(frame).nunique() == 1


# --------------------------------------------------------------------------
# Namespacing — two datasets must never write over each other
# --------------------------------------------------------------------------


def test_paths_are_namespaced_per_dataset():
    assert CREDITCARD.processed_dir != IEEECIS.processed_dir
    assert CREDITCARD.results_dir != IEEECIS.results_dir
    assert CREDITCARD.processed_dir.name == "creditcard"
    assert IEEECIS.results_dir.name == "ieeecis"


def test_split_paths_sit_under_the_dataset_directory():
    for spec in SPECS.values():
        assert spec.split_path("dev").parent == spec.processed_dir
        assert spec.split_manifest_path.parent == spec.processed_dir


# --------------------------------------------------------------------------
# Internal consistency
# --------------------------------------------------------------------------


def test_multi_table_spec_requires_a_join_key():
    with pytest.raises(DatasetError, match="no join_key"):
        DatasetSpec(
            name="bad",
            raw_paths={"a": CREDITCARD.primary_path, "b": CREDITCARD.primary_path},
            join_key=None,
            time_column="Time",
            target_column="Class",
            amount_column="Amount",
            entity_keys=None,
        )


@pytest.mark.parametrize("fraction", [0.0, 1.0, -0.1, 1.5])
def test_holdout_fraction_must_be_a_proper_fraction(fraction):
    with pytest.raises(DatasetError, match="holdout_fraction"):
        DatasetSpec(
            name="bad",
            raw_paths={"t": CREDITCARD.primary_path},
            join_key=None,
            time_column="Time",
            target_column="Class",
            amount_column="Amount",
            entity_keys=None,
            holdout_fraction=fraction,
        )


def test_fold_counts_reflect_the_available_positives():
    """Not a preference: the fold count is chosen from fraud per validation
    block. IEEE-CIS carries 42x more positives, so it can afford more folds."""
    assert CREDITCARD.n_cv_folds == 4
    assert IEEECIS.n_cv_folds == 6
    assert IEEECIS.expected_fraud > CREDITCARD.expected_fraud * 40


def test_specs_are_immutable():
    with pytest.raises(Exception):
        CREDITCARD.n_cv_folds = 99  # type: ignore[misc]


def test_record_payload_is_json_serializable():
    import json

    for spec in SPECS.values():
        json.dumps(spec.to_dict())


def test_ieee_declares_only_the_labelled_tables():
    """`test_transaction.csv` has no `isFraud` column — it is the competition
    test set and its labels are held by the organisers. Pointing the spec at it
    would produce a frame that fails validation."""
    names = {p.name for p in IEEECIS.raw_paths.values()}
    assert names == {"train_transaction.csv", "train_identity.csv"}


# --------------------------------------------------------------------------
# Regression: the --dataset flag must actually reach the runner
# --------------------------------------------------------------------------


def test_run_and_report_passes_the_spec_through(monkeypatch):
    """Regression guard for a real bug.

    `run_and_report` once called `run_cv` without forwarding `spec`, so every
    run silently used the default dataset. It failed in the worst possible way:
    the run succeeded, printed plausible numbers, and wrote a valid record —
    only against the wrong data. Nothing in the output said so.
    """
    from src.evaluation import runner

    captured: dict = {}

    def fake_run_cv(model_factory, **kwargs):
        captured.update(kwargs)
        raise RuntimeError("stop here — the call itself is what is under test")

    monkeypatch.setattr(runner, "run_cv", fake_run_cv)

    with pytest.raises(RuntimeError, match="stop here"):
        runner.run_and_report("xgboost", spec=IEEECIS)

    assert captured["spec"] is IEEECIS, "the requested dataset never reached run_cv"


def test_results_of_two_datasets_cannot_collide():
    """Same model name, different dataset: separate trees, so a paired
    comparison across datasets is hard to make by accident."""
    from src.evaluation import runner

    assert runner.result_dir("xgboost", CREDITCARD) != runner.result_dir("xgboost", IEEECIS)
    assert runner.result_dir("xgboost", IEEECIS).parent.name == "ieeecis"
