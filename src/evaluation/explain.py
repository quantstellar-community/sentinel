"""Layer 10 — Explanation: evidence for an alert that a person can check.

Design principle #5 of the project is *explainability by design*, and this is
where it stops being an aspiration. Two products:

* **Attribution.** Exact TreeSHAP contributions, so a score decomposes into
  named features that sum back to it.
* **Counterfactual.** The smallest change to something a person could actually
  do that would take the alert away.

## Attribution comes from the booster, not from a package

XGBoost and LightGBM both implement TreeSHAP internally. The standalone `shap`
package calls the same algorithm for tree models, so wrapping it would add a
dependency and no accuracy. Contributions are in *margin* space because that is
where they are additive, and additivity is the whole reason an attribution is
worth reporting: `bias + sum(contributions) == margin`, checkable per row.

## The counterfactual recomputes rather than reconstructs

PIPELINE_V2 §12 specifies causal propagation through explicit formulas — change
`amount`, then update `SUM_AMOUNT_w`, `AMOUNT_Z_SCORE`, each velocity ratio, and
so on. The reasoning is right and the failure it names is real: perturbing one
cell of the feature matrix and rescoring produces a state that could not exist,
so the recommendation is arithmetic nonsense.

This implements the same requirement a different way. Rather than restating each
formula, it perturbs the **raw** column and re-runs the feature pipeline. Three
advantages, and the third is the one that matters:

1. It is exact, because it runs the same code that built the features.
2. It cannot drift out of sync — a new feature group is covered the day it lands,
   with no propagation rule to remember to write.
3. It propagates further than the formulas do. Changing a transaction's amount
   also changes the history that the entity's *later* transactions inherit, and
   a hand-written rule set stops at the row being explained.

## Immutable features are blocked at layer 1

`spec.mutable_columns` decides what may be proposed, defaulting to the amount
alone. On these two datasets that is not a limitation but an accurate reading:
IEEE-CIS is anonymised and creditcard's `V1`-`V28` are PCA components, so
"lower V17" is not advice anyone can follow.

## What a search over a tree ensemble can and cannot promise

A tree ensemble is a step function, not a monotone one, so a bisection alone can
land in a pocket and report a change that is neither minimal nor real. The
search here scans a grid first to find where the score genuinely crosses, then
bisects only inside that bracket. The bracket is exact; the refinement inside it
assumes the crossing is local, which is the one assumption this cannot discharge
and therefore states.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.datasets import DatasetSpec, get_spec
from src.features import FeaturePipeline
from src.models.base import SentinelModel


class ExplanationError(RuntimeError):
    """Raised when an explanation cannot be produced honestly."""


@dataclass
class Attribution:
    """One feature's signed contribution to a single score."""

    feature: str
    value: float
    contribution: float

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "value": None if pd.isna(self.value) else float(self.value),
            "contribution": float(self.contribution),
        }


@dataclass
class Explanation:
    """A decomposed score: bias plus contributions, summing to the margin."""

    index: object
    risk_score: float
    bias: float
    margin: float
    attributions: list[Attribution] = field(repr=False)

    def top(self, k: int = 3, positive_only: bool = True) -> list[Attribution]:
        """The `k` features that pushed the score up the most.

        Ranked by signed contribution rather than magnitude: a feature arguing
        strongly *against* fraud is not evidence for the alert, and listing it
        among the reasons would misrepresent the model.
        """
        ranked = sorted(self.attributions, key=lambda a: -a.contribution)
        if positive_only:
            ranked = [a for a in ranked if a.contribution > 0]
        return ranked[:k]

    def check_additivity(self, tolerance: float = 1e-4) -> None:
        """The property that makes an attribution meaningful rather than a ranking."""
        total = self.bias + sum(a.contribution for a in self.attributions)
        if abs(total - self.margin) > tolerance:
            raise ExplanationError(
                f"contributions sum to {total:.6f} but the model's margin is "
                f"{self.margin:.6f}. These are not exact SHAP values."
            )

    def to_dict(self, k: int = 3) -> dict:
        return {
            "index": str(self.index),
            "risk_score": float(self.risk_score),
            "bias": float(self.bias),
            "margin": float(self.margin),
            "top_reasons": [a.to_dict() for a in self.top(k)],
        }


def explain(model: SentinelModel, X: pd.DataFrame) -> list[Explanation]:
    """Attribute each row's score to its features, exactly."""
    if not model.explainable:
        raise ExplanationError(
            f"{model.name} does not attribute its score. Layer 10 covers tree "
            "ensembles; an anomaly score has no additive decomposition to report."
        )

    contributions = np.asarray(model.shap_contributions(X), dtype="float64")
    expected = (len(X), len(X.columns) + 1)
    if contributions.shape != expected:
        raise ExplanationError(
            f"{model.name} returned contributions of shape {contributions.shape}, "
            f"expected {expected} (one column per feature plus a bias)"
        )

    scores = np.asarray(model.risk_score(X), dtype="float64")
    margins = contributions.sum(axis=1)

    return [
        Explanation(
            index=X.index[i],
            risk_score=float(scores[i]),
            bias=float(contributions[i, -1]),
            margin=float(margins[i]),
            attributions=[
                Attribution(column, X.iloc[i][column], contributions[i, j])
                for j, column in enumerate(X.columns)
            ],
        )
        for i in range(len(X))
    ]


# --------------------------------------------------------------------------
# Counterfactual
# --------------------------------------------------------------------------


@dataclass
class Counterfactual:
    """The smallest actionable change that clears the alert, or its absence."""

    column: str
    original: float
    proposed: float | None
    original_score: float
    proposed_score: float | None
    threshold: float
    n_evaluations: int
    #: Set when no value in the searched range clears the threshold. An honest
    #: "nothing you could do about this one" beats a fabricated number.
    unreachable: bool = False

    @property
    def change(self) -> float | None:
        return None if self.proposed is None else self.proposed - self.original

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "original": float(self.original),
            "proposed": None if self.proposed is None else float(self.proposed),
            "change": None if self.change is None else float(self.change),
            "original_score": float(self.original_score),
            "proposed_score": (
                None if self.proposed_score is None else float(self.proposed_score)
            ),
            "threshold": float(self.threshold),
            "n_evaluations": self.n_evaluations,
            "unreachable": self.unreachable,
        }


def _score_with(
    model: SentinelModel,
    pipeline: FeaturePipeline,
    raw: pd.DataFrame,
    position: int,
    column: str,
    value: float,
    columns: list[str],
) -> float:
    """Set one raw cell, rebuild every feature, and rescore the row.

    Rebuilding is what makes the result a state the data could actually contain.
    Editing the feature matrix directly would leave `SUM_AMOUNT_24H` describing
    an amount the row no longer has.
    """
    perturbed = raw.copy()
    perturbed.iloc[position, perturbed.columns.get_loc(column)] = value

    features = pipeline.transform(perturbed)
    return float(model.risk_score(features[columns].iloc[[position]])[0])


def _narrow_to_entity(
    raw: pd.DataFrame, position: int, spec: DatasetSpec
) -> tuple[pd.DataFrame, int, list | None]:
    """Cut the frame down to the rows that can affect this row's features.

    A counterfactual re-runs the pipeline once per candidate value, so handing
    it the whole validation fold means rebuilding 67,000 rows of features to
    learn about one. Narrowing to the entity is not an approximation: the
    behavioural groups are functions of the entity's own history and nothing
    else, which `test_one_entitys_rows_do_not_reach_another` establishes
    independently. Training history still arrives through the fitted pipeline.

    Datasets without entities narrow to the single row, since every remaining
    group is row-wise.
    """
    if not spec.has_entity:
        return raw.iloc[[position]], 0, None

    entity = spec.entity_id(raw)
    wanted = entity.iloc[position]
    same = (entity == wanted).to_numpy()
    return raw.loc[same], int(same[:position].sum()), [wanted]


def counterfactual(
    model: SentinelModel,
    pipeline: FeaturePipeline,
    raw: pd.DataFrame,
    position: int,
    *,
    threshold: float,
    spec: DatasetSpec | str | None = None,
    column: str | None = None,
    n_grid: int = 24,
    n_refine: int = 12,
) -> Counterfactual:
    """Smallest change to a mutable raw column that drops the score below `threshold`.

    `raw` must carry the row's own context — the entity's earlier transactions —
    because the behavioural features are functions of that history. Passing the
    row alone would silently produce a customer with no past.
    """
    spec = get_spec(spec)
    raw, position, entities = _narrow_to_entity(raw, position, spec)
    # The stored history has to shrink too. Narrowing only the frame leaves the
    # groups re-deriving a whole training fold of history per candidate value,
    # which is the difference between an explanation that takes a second and one
    # that takes minutes.
    pipeline = pipeline.narrowed_to(entities) if entities is not None else pipeline
    column = column or spec.mutable_columns[0]
    if column not in spec.mutable_columns:
        raise ExplanationError(
            f"{column!r} is not in spec.mutable_columns {spec.mutable_columns}. "
            "A counterfactual on an immutable field is not a recommendation — "
            "'be younger' is not advice."
        )
    if column not in raw.columns:
        raise ExplanationError(f"{column!r} is not a column of the supplied frame")

    columns = model.select_features(list(pipeline.transform(raw).columns), spec)
    original = float(raw.iloc[position][column])
    baseline = _score_with(
        model, pipeline, raw, position, column, original, columns
    )
    evaluations = 1

    if baseline < threshold:
        return Counterfactual(
            column=column,
            original=original,
            proposed=original,
            original_score=baseline,
            proposed_score=baseline,
            threshold=threshold,
            n_evaluations=evaluations,
        )

    # Scan downward from the original. A grid rather than a bisection because a
    # tree ensemble is a step function: bisecting a non-monotone score can settle
    # in a pocket and report a change that does not hold on either side of it.
    grid = np.linspace(0.0, original, n_grid)
    passing: tuple[float, float] | None = None
    failing_above = original
    for value in reversed(grid[:-1]):  # nearest change first
        score = _score_with(model, pipeline, raw, position, column, value, columns)
        evaluations += 1
        if score < threshold:
            passing = (float(value), score)
            break
        failing_above = float(value)

    if passing is None:
        return Counterfactual(
            column=column,
            original=original,
            proposed=None,
            original_score=baseline,
            proposed_score=None,
            threshold=threshold,
            n_evaluations=evaluations,
            unreachable=True,
        )

    # Refine inside the bracket only. The crossing is known to lie here; whether
    # it is the single crossing is the assumption this cannot discharge.
    low, low_score = passing
    high = failing_above
    for _ in range(n_refine):
        middle = 0.5 * (low + high)
        score = _score_with(model, pipeline, raw, position, column, middle, columns)
        evaluations += 1
        if score < threshold:
            low, low_score = middle, score
        else:
            high = middle

    return Counterfactual(
        column=column,
        original=original,
        proposed=low,
        original_score=baseline,
        proposed_score=low_score,
        threshold=threshold,
        n_evaluations=evaluations,
    )


__all__ = [
    "Attribution",
    "Counterfactual",
    "Explanation",
    "ExplanationError",
    "counterfactual",
    "explain",
]
