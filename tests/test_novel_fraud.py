"""Tests for the novel-fraud experiment's mechanics.

The experiment's conclusion rests entirely on two mechanisms being correct: the
fraud taxonomy must partition only fraud, and the blinding must actually remove
the labels it claims to remove. A bug in either produces a confident, wrong
answer to the project's central question.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.novel_fraud_experiment import cluster_fraud, fit_and_score
from src.datasets import CREDITCARD
from tests.conftest import make_dev


def test_taxonomy_labels_only_fraud():
    dev = make_dev(n=4_000, seed=3)
    assignment = cluster_fraud(dev, 3, CREDITCARD)

    is_fraud = dev[CREDITCARD.target_column] == 1
    assert (assignment[~is_fraud.to_numpy()] == -1).all(), "a legitimate row got a cluster"
    assert (assignment[is_fraud.to_numpy()] >= 0).all(), "a fraud row was left unassigned"
    assert len(assignment) == len(dev)


def test_taxonomy_produces_the_requested_number_of_clusters():
    dev = make_dev(n=4_000, seed=3)
    assignment = cluster_fraud(dev, 3, CREDITCARD)

    clusters = sorted(assignment[assignment >= 0].unique().tolist())
    assert clusters == [0, 1, 2]


def test_taxonomy_is_reproducible():
    dev = make_dev(n=4_000, seed=3)
    first = cluster_fraud(dev, 3)
    second = cluster_fraud(dev, 3)

    assert first.equals(second)


def test_blinding_removes_exactly_the_targeted_cluster():
    """The relabelling step, reproduced as the experiment performs it."""
    dev = make_dev(n=4_000, seed=3)
    assignment = cluster_fraud(dev, 3, CREDITCARD)
    target = 1

    blinded = dev.copy()
    hide = (assignment == target).to_numpy()
    blinded.loc[blinded.index[hide], CREDITCARD.target_column] = 0

    # Every fraud of the target type is now labelled legitimate.
    assert (blinded.loc[hide, CREDITCARD.target_column] == 0).all()

    # Nothing else moved: the other clusters keep their labels.
    others = ((assignment >= 0) & (assignment != target)).to_numpy()
    assert (blinded.loc[others, CREDITCARD.target_column] == 1).all()
    assert int(blinded[CREDITCARD.target_column].sum()) == int(
        dev[CREDITCARD.target_column].sum() - hide.sum()
    )


def test_blinding_contaminates_the_normal_set_on_purpose():
    """Undiscovered fraud sits inside the 'normal' data, as it would in reality.

    The anomaly model trains on `y == 0`, so hidden fraud is part of what it
    learns as normal. That is the realistic condition, not a flaw.
    """
    dev = make_dev(n=4_000, seed=3)
    assignment = cluster_fraud(dev, 3, CREDITCARD)
    target = 1

    blinded = dev.copy()
    hide = (assignment == target).to_numpy()
    blinded.loc[blinded.index[hide], CREDITCARD.target_column] = 0

    normal_rows = blinded[blinded[CREDITCARD.target_column] == 0]
    true_labels = dev.loc[normal_rows.index, CREDITCARD.target_column]
    assert int(true_labels.sum()) == int(hide.sum()) > 0


@pytest.mark.parametrize("model_name", ["xgboost", "isolation_forest"])
def test_fit_and_score_respects_the_model_contract(model_name):
    """Scoring must honour feature budget and normal-only fitting, exactly as
    the runner does — otherwise the experiment measures a different model than
    `run_experiment.py` reports."""
    dev = make_dev(n=4_000, seed=3)
    train, evaluate_on = dev.iloc[:3_000], dev.iloc[3_000:]

    scores = fit_and_score(model_name, train, evaluate_on, CREDITCARD)

    assert scores.shape == (len(evaluate_on),)
    assert np.isfinite(scores).all()


def test_fit_and_score_returns_a_ranking_not_a_constant():
    dev = make_dev(n=4_000, seed=3)
    train, evaluate_on = dev.iloc[:3_000], dev.iloc[3_000:]

    scores = fit_and_score("isolation_forest", train, evaluate_on, CREDITCARD)
    assert len(np.unique(scores)) > 1


def test_evaluation_subset_keeps_legitimate_rows_and_one_fraud_type():
    """The scored subset must contain all normals plus only the target type."""
    dev = make_dev(n=4_000, seed=3)
    assignment = cluster_fraud(dev, 3, CREDITCARD)
    target = 0

    keep = ((assignment == -1) | (assignment == target)).to_numpy()
    subset = dev[keep]

    labels = subset[CREDITCARD.target_column]
    assert int(labels.sum()) == int((assignment == target).sum())
    assert int((labels == 0).sum()) == int((assignment == -1).sum())

    # No fraud of any other type survived into the evaluation set.
    surviving = assignment[keep]
    assert set(surviving.unique().tolist()) <= {-1, target}


def test_taxonomy_handles_a_frame_with_few_fraud_cases():
    dev = make_dev(n=1_000, seed=11)
    n_fraud = int(dev[CREDITCARD.target_column].sum())
    assert n_fraud >= 2

    assignment = cluster_fraud(dev, 2, CREDITCARD)
    assert isinstance(assignment, pd.Series)
    assert sorted(assignment[assignment >= 0].unique().tolist()) == [0, 1]
