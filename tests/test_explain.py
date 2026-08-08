"""Layer 10 tests.

Two properties carry this layer, and both are the kind that fail silently.

**Additivity.** An attribution is worth reporting only because `bias + sum(
contributions)` reconstructs the model's own output. Without that it is a
plausible-looking ranking with no claim behind it, and nothing in the numbers
would say so.

**Causal propagation.** A counterfactual that edits one cell of the feature
matrix describes a state the data could not contain — an amount of 50 sitting
beside a `SUM_AMOUNT_1H` that still reflects 4,000. It produces a number, the
number looks reasonable, and the advice is arithmetic nonsense. The test for it
has to compare against the naive version rather than merely assert the correct
one runs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import CREDITCARD, IEEECIS
from src.evaluation import explain
from src.evaluation.runner import pipeline_for
from src.models import get_model
from tests.conftest import make_dev


def fitted(model_name: str = "xgboost_behavioral", spec=IEEECIS, n: int = 1_200):
    """A fitted model plus everything a counterfactual needs around it."""
    dev = make_dev(spec, n=n, n_unique_times=n // 2)
    train, test = dev.iloc[: n * 2 // 3], dev.iloc[n * 2 // 3 :]

    model = get_model(model_name, spec)
    pipeline = pipeline_for(model, spec).fit(train)
    X = pipeline.transform(train)
    columns = model.select_features(list(X.columns), spec)
    model.fit(X[columns], train[spec.target_column])

    return model, pipeline, train, test, columns


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------


def test_contributions_reconstruct_the_models_own_output():
    """The one property that separates SHAP values from a feature ranking."""
    model, pipeline, _, test, columns = fitted()
    X = pipeline.transform(test)[columns].head(10)

    for explanation in explain.explain(model, X):
        explanation.check_additivity()


def test_a_broken_additivity_is_caught():
    broken = explain.Explanation(
        index=0,
        risk_score=0.9,
        bias=1.0,
        margin=5.0,
        attributions=[explain.Attribution("f", 1.0, 0.5)],
    )
    with pytest.raises(explain.ExplanationError, match="not exact SHAP values"):
        broken.check_additivity()


def test_both_boosting_families_attribute_exactly():
    for name in ("xgboost", "lightgbm"):
        model, pipeline, _, test, columns = fitted(name, CREDITCARD)
        X = pipeline.transform(test)[columns].head(5)

        assert model.explainable is True
        for explanation in explain.explain(model, X):
            explanation.check_additivity()


def test_a_model_that_cannot_attribute_says_so():
    """An anomaly score has no additive decomposition; inventing one would be
    the "evidence over hype" principle failing in the explanation layer."""
    model, pipeline, _, test, columns = fitted("isolation_forest", CREDITCARD)
    X = pipeline.transform(test)[columns].head(3)

    assert model.explainable is False
    with pytest.raises(explain.ExplanationError, match="does not attribute"):
        explain.explain(model, X)


def test_top_reasons_are_evidence_for_the_alert_not_against_it():
    """Ranked by signed contribution, not magnitude. A feature arguing strongly
    that a row is legitimate is not a reason the row was flagged."""
    explanation = explain.Explanation(
        index=0,
        risk_score=0.9,
        bias=0.0,
        margin=0.0,
        attributions=[
            explain.Attribution("strongly_against", 1.0, -5.0),
            explain.Attribution("weakly_for", 1.0, 0.1),
            explain.Attribution("strongly_for", 1.0, 2.0),
        ],
    )
    top = explanation.top(k=3)

    assert [a.feature for a in top] == ["strongly_for", "weakly_for"]
    assert all(a.contribution > 0 for a in top)


# --------------------------------------------------------------------------
# Causal propagation — the reason this layer is not a one-liner
# --------------------------------------------------------------------------


def test_changing_the_raw_amount_moves_every_feature_derived_from_it():
    model, pipeline, _, test, columns = fitted()
    position = 5

    before = pipeline.transform(test)[columns].iloc[[position]]
    perturbed = test.copy()
    perturbed.iloc[position, perturbed.columns.get_loc(IEEECIS.amount_column)] = 1.0
    after = pipeline.transform(perturbed)[columns].iloc[[position]]

    moved = [
        c
        for c in columns
        if not np.allclose(before[c].fillna(-999.0), after[c].fillna(-999.0))
    ]

    assert IEEECIS.amount_column in moved
    assert any(c.startswith("SUM_AMOUNT_") for c in moved), "window sums must follow"
    assert "AMOUNT_Z_SCORE" in moved, "the z-score is a function of the amount"


def test_editing_the_feature_matrix_directly_produces_an_impossible_state():
    """Why the counterfactual rebuilds instead of substituting.

    The naive perturbation leaves the derived columns describing an amount the
    row no longer has. It raises nothing and scores fine — which is exactly why
    it needs a test naming it rather than a comment warning about it.
    """
    model, pipeline, _, test, columns = fitted()
    position = 5
    new_amount = 1.0

    naive = pipeline.transform(test)[columns].iloc[[position]].copy()
    naive[IEEECIS.amount_column] = new_amount

    perturbed = test.copy()
    perturbed.iloc[position, perturbed.columns.get_loc(IEEECIS.amount_column)] = new_amount
    rebuilt = pipeline.transform(perturbed)[columns].iloc[[position]]

    assert naive[IEEECIS.amount_column].iloc[0] == rebuilt[IEEECIS.amount_column].iloc[0]
    assert naive["AMOUNT_Z_SCORE"].iloc[0] != rebuilt["AMOUNT_Z_SCORE"].iloc[0], (
        "the naive edit left the z-score describing the old amount"
    )


def test_velocity_ratios_correctly_stay_put_when_they_should():
    """A ratio whose numerator and denominator both scale with the amount is
    unchanged by it. Getting this right is free when the features are recomputed
    and easy to get wrong when the propagation is written out by hand."""
    model, pipeline, _, test, columns = fitted()
    position = 5

    before = pipeline.transform(test)[columns].iloc[[position]]
    perturbed = test.copy()
    perturbed.iloc[position, perturbed.columns.get_loc(IEEECIS.amount_column)] = 2.0
    after = pipeline.transform(perturbed)[columns].iloc[[position]]

    count_ratios = [c for c in columns if c.startswith("VELOCITY_COUNT_")]
    for column in count_ratios:
        assert np.allclose(before[column], after[column]), (
            f"{column} counts transactions and cannot depend on the amount"
        )


# --------------------------------------------------------------------------
# What may be proposed
# --------------------------------------------------------------------------


def test_an_immutable_column_cannot_be_proposed():
    """"Be ten years younger" is not a recommendation. On these datasets almost
    everything is immutable, and that is an accurate reading rather than a gap:
    anonymised components carry no action a person could take."""
    model, pipeline, _, test, _ = fitted()

    with pytest.raises(explain.ExplanationError, match="not a recommendation"):
        explain.counterfactual(
            model, pipeline, test, 0, threshold=0.5, spec=IEEECIS, column="card1"
        )


def test_the_amount_is_mutable_on_both_datasets():
    assert IEEECIS.mutable_columns == [IEEECIS.amount_column]
    assert CREDITCARD.mutable_columns == [CREDITCARD.amount_column]


# --------------------------------------------------------------------------
# The search
# --------------------------------------------------------------------------


def test_narrowing_to_the_entity_changes_no_answer():
    """The optimisation that makes this layer usable, stated as a property.

    Re-running the pipeline per candidate over a whole validation fold rebuilds
    tens of thousands of rows to learn about one. Narrowing to the entity is
    sound because the behavioural groups read that entity's history and nothing
    else — but "sound because I reasoned about it" is how the leakage bugs in
    this project started, so it is checked against the wide frame directly.
    """
    model, pipeline, _, test, columns = fitted()
    position = int(np.argmax(model.risk_score(pipeline.transform(test)[columns])))

    narrow, narrow_position, entities = explain._narrow_to_entity(test, position, IEEECIS)

    assert len(narrow) < len(test), "the whole point is to look at fewer rows"
    assert narrow.index[narrow_position] == test.index[position], (
        "the row being explained must survive the narrowing"
    )

    # Both halves must narrow: the frame *and* the history the pipeline stores.
    # Cutting only the frame leaves each candidate re-deriving a whole training
    # fold, which is the difference between seconds and minutes.
    narrow_pipeline = pipeline.narrowed_to(entities)

    wide_features = pipeline.transform(test)[columns].iloc[[position]]
    narrow_features = narrow_pipeline.transform(narrow)[columns].iloc[[narrow_position]]
    pd.testing.assert_frame_equal(wide_features, narrow_features)


def test_narrowing_the_pipeline_leaves_the_original_intact():
    """An experiment may still be using the pipeline this was narrowed from."""
    model, pipeline, _, test, columns = fitted()
    before = pipeline.transform(test)[columns]

    pipeline.narrowed_to(["nobody"])

    pd.testing.assert_frame_equal(pipeline.transform(test)[columns], before)


def test_narrowing_keeps_a_single_row_when_there_are_no_entities():
    model, pipeline, _, test, _ = fitted("xgboost", CREDITCARD)
    narrow, position, entities = explain._narrow_to_entity(test, 4, CREDITCARD)

    assert len(narrow) == 1
    assert position == 0
    assert entities is None, "there is no entity to narrow a history to"
    assert narrow.index[0] == test.index[4]


def test_a_row_already_below_the_threshold_needs_no_change():
    model, pipeline, _, test, columns = fitted()
    scores = model.risk_score(pipeline.transform(test)[columns])
    safest = int(np.argmin(scores))

    result = explain.counterfactual(
        model, pipeline, test, safest, threshold=0.99, spec=IEEECIS
    )

    assert result.change == 0.0
    assert result.unreachable is False


def test_a_reachable_counterfactual_actually_clears_the_threshold():
    model, pipeline, _, test, columns = fitted()
    scores = model.risk_score(pipeline.transform(test)[columns])
    riskiest = int(np.argmax(scores))
    threshold = float(scores[riskiest]) * 0.5

    result = explain.counterfactual(
        model, pipeline, test, riskiest, threshold=threshold, spec=IEEECIS
    )

    if not result.unreachable:
        assert result.proposed_score < threshold
        assert result.proposed < result.original, "clearing an alert means spending less"


def test_an_unreachable_counterfactual_is_reported_rather_than_invented():
    """Some alerts do not turn on the amount at all. Saying so is the honest
    answer; manufacturing a number would not be."""

    class AlwaysFlagging:
        name = "always"
        explainable = False

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, item):
            return getattr(self._inner, item)

        def risk_score(self, X):
            return np.ones(len(X))

    model, pipeline, _, test, _ = fitted()
    result = explain.counterfactual(
        AlwaysFlagging(model), pipeline, test, 0, threshold=0.5, spec=IEEECIS
    )

    assert result.unreachable is True
    assert result.proposed is None
    assert result.to_dict()["proposed"] is None


def test_the_payload_is_json_serializable():
    import json

    model, pipeline, _, test, columns = fitted()
    X = pipeline.transform(test)[columns].head(3)

    for explanation in explain.explain(model, X):
        json.dumps(explanation.to_dict())

    json.dumps(
        explain.counterfactual(
            model, pipeline, test, 0, threshold=0.5, spec=IEEECIS
        ).to_dict()
    )
