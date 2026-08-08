"""Hyperparameter search, performed inside the training fold.

Until now every model in this project ran on hand-set constants. That was the
right starting point — a tuned model and an untuned one are not comparable, and
the protocol needed fixed baselines before it could measure anything. But it
leaves an obvious question unanswered, and one measurement makes the size of it
concrete: `lightgbm_unweighted` scores 0.5937 on IEEE-CIS against `xgboost`'s
0.5393, a 10% relative gap produced by a *single binary flag*. If one flag is
worth that, the rest of the space is worth looking at.

## Why this is a wrapper rather than a script

A tuning script would select hyperparameters once, on data that includes every
evaluation fold, and every number downstream would be optimistic by an amount
nobody could estimate. That is the classic form of the leak and it leaves no
trace in the output.

Here the search happens inside `fit`, which by construction only ever receives a
training fold. The nesting *is* the guarantee — the same argument
`AnomalyAugmentedModel` relies on. There is no check to forget, because there is
no code path that could reach the evaluation rows.

## The inner split

`fit` carves its own validation slice off the end of the training fold, searches
against it, then refits the winner on the whole fold.

That slice is taken **by position**, which is correct only because the frame
arrives in time order: the runner slices a time-sorted development set with
contiguous indices, and neither the feature pipeline nor the label regime
reorders rows. `_assert_time_ordered` checks it whenever the time column
survives into the feature matrix, so the assumption is verified rather than
trusted wherever verification is possible.

## What this changes about early stopping

`supervised.py` records a decision not to use early stopping, because it would
carve a validation slice out of each training fold and introduce a second,
undocumented split. That reasoning was right for a fixed baseline. It does not
apply here: this layer's whole purpose is an explicit, documented inner split.
Early stopping is still left off for now, so that the refit uses exactly the
configuration that was scored — introducing it would make the number of trees at
refit differ from the number that won the search, which is a separate decision
needing its own measurement.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src import config
from src.datasets import DatasetSpec
from src.features import FeatureGroup
from src.models.base import ScaleSpec, SentinelModel

#: Fraction of the training fold held back to score candidates on. A quarter
#: keeps enough positives to rank candidates on IEEE-CIS (~450 in the smallest
#: fold) while leaving most of the history to fit on.
DEFAULT_INNER_FRACTION = 0.25

#: Below this many positives in the inner slice, AUPRC ranks noise rather than
#: candidates and the search would select on chance. Chosen against creditcard,
#: where a fold holds 47-89 fraud cases in total: a quarter of that is ~17, and
#: a search on 17 positives is not a search.
MIN_INNER_POSITIVES = 50


class TuningError(RuntimeError):
    """Raised when a search cannot be run honestly."""


#: `balanced` is in both spaces on purpose. It is the flag whose two settings
#: already measured 0.5393 against 0.5790 on IEEE-CIS and moved in the *opposite*
#: direction on creditcard, so it is the one hyperparameter known to matter and
#: known not to have a universal answer. A search that fixed it would be
#: assuming away the only thing already proven to be dataset-dependent.
#:
#: Ranges are kept deliberately narrow around the recorded baselines rather than
#: spanning everything plausible: the cost is linear in candidates and each
#: candidate is a full fit on up to 300,000 rows.
XGBOOST_SPACE: dict[str, list] = {
    "balanced": [True, False],
    "max_depth": [3, 4, 5, 6, 8],
    "learning_rate": [0.02, 0.05, 0.1, 0.2],
    "n_estimators": [200, 400, 600],
    "min_child_weight": [1, 5, 20, 50],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.4, 0.6, 0.8],
    "reg_lambda": [0.1, 1.0, 10.0],
}

#: `min_child_samples` and `reg_lambda` start above LightGBM's own defaults. Both
#: were raised in the baseline for a measured reason — an unpenalised leaf under
#: `scale_pos_weight` near 578 saturated the output to 65 distinct scores across
#: 45,397 rows — and the search should explore around that fix rather than back
#: through the failure it corrected.
LIGHTGBM_SPACE: dict[str, list] = {
    "balanced": [True, False],
    "num_leaves": [15, 31, 63, 127],
    "learning_rate": [0.02, 0.05, 0.1, 0.2],
    "n_estimators": [200, 400, 600],
    "min_child_samples": [20, 50, 100, 200],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.4, 0.6, 0.8],
    "reg_lambda": [0.1, 1.0, 10.0],
}


#: Logistic regression has one parameter that genuinely matters — the inverse
#: regularisation strength `C` — and two modelling choices the registry already
#: answers separately for the untuned baselines. Putting all three in one space
#: lets the search find combinations a per-flag comparison cannot: the best `C`
#: under `class_weight="balanced"` need not be the best `C` without it.
#:
#: `penalty` is deliberately absent. L1 requires a different solver, and a random
#: draw pairing `l1` with the default `lbfgs` raises rather than scoring badly —
#: a search space whose points are not all valid is a source of crashes, not of
#: candidates.
LOGREG_SPACE: dict[str, list] = {
    "C": [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
    "class_weight": ["balanced", None],
}

#: Parameters a search space must not contain, and what to do instead.
#:
#: These are consumed by layer 7 *before* `fit` is called, so a candidate that
#: declares one is handed a matrix that was already built under the outer
#: model's declaration. The candidate's own value is set and then never read —
#: an inert dimension that silently halves the effective budget while looking
#: like it doubled the coverage.
#:
#: Found the hard way: `LOGREG_SPACE` briefly carried `scale_columns`, and the
#: search trace gave identical inner scores in pairs differing only in that key.
#: Eight draws explored five distinct configurations.
INERT_IN_SEARCH: dict[str, str] = {
    "scale_columns": (
        "preprocessing is resolved by the runner before fit() is called, so a "
        "candidate cannot change it. Register two models with different "
        "scale_columns instead — that is what logreg vs logreg_full_scale is."
    ),
    "requires_entity": "decides which datasets the model runs on, not how it fits",
    "label_regime": "the label budget is a track, not a hyperparameter",
    "handles_missing": "consumed by the runner's imputation step, before fit()",
}


def _assert_time_ordered(X: pd.DataFrame, spec: DatasetSpec) -> None:
    """Verify the positional inner split really is a temporal one.

    Only possible when the time column survived feature selection — anomaly
    models drop it. When it is absent the ordering still holds for the reason
    given in the module docstring; this catches the case where it does not.
    """
    column = spec.time_column
    if column in X.columns and not X[column].is_monotonic_increasing:
        raise TuningError(
            f"{column} is not increasing in the training fold, so splitting by "
            "position would not split by time. The search would train on the "
            "future of its own validation slice."
        )


class TunedModel(SentinelModel):
    """Selects hyperparameters inside the training fold, then refits on it.

    Every declaration the runner reads — scaling, missing-value handling, label
    regime, feature groups — is delegated to the wrapped model rather than
    restated, so wrapping cannot silently change the contract the untuned
    baseline was measured under. That matters: the comparison this exists to
    support is `xgboost` against `xgboost_tuned`, and it is only a comparison if
    hyperparameters are the one thing that differs.
    """

    def __init__(
        self,
        factory: Callable[..., SentinelModel],
        space: dict[str, Sequence],
        *,
        name: str,
        n_candidates: int = 16,
        inner_fraction: float = DEFAULT_INNER_FRACTION,
        min_inner_positives: int = MIN_INNER_POSITIVES,
        seed: int = config.SEED,
    ):
        inert = sorted(set(space) & set(INERT_IN_SEARCH))
        if inert:
            reasons = "\n  ".join(f"{k}: {INERT_IN_SEARCH[k]}" for k in inert)
            raise TuningError(
                f"{name}: these keys cannot be searched because the runner reads "
                f"them before fit() and a candidate's value is never consulted:\n"
                f"  {reasons}\n"
                "Leaving them in does not widen the search — it silently spends "
                "the candidate budget on duplicates."
            )

        self.name = name
        self._factory = factory
        self._space = {key: list(values) for key, values in space.items()}
        self.n_candidates = n_candidates
        self.inner_fraction = inner_fraction
        self.min_inner_positives = min_inner_positives
        self.seed = seed

        # A prototype carries the wrapped model's declarations. Built once at
        # construction because the runner reads several of them before `fit`.
        prototype = factory()

        # Candidates are ranked by AUPRC on held-back rows, which needs
        # positives in the `y` that reaches `fit`. Track B filters them out and
        # track C zeroes them, so in both cases the objective silently becomes
        # undefined rather than wrong — and would surface as the unhelpful
        # "0 positives" message from the guard below.
        regime = prototype.label_regime
        if regime.filters_to_normal or not regime.sees_labels:
            raise TuningError(
                f"{name}: cannot rank candidates by AUPRC on a model in the "
                f"{regime.name!r} regime — no positive reaches `fit`, so the "
                "objective does not exist. Tuning an anomaly model needs an "
                "objective that works without labels, which is a separate "
                "design rather than a parameter of this one."
            )
        self.scale_columns: ScaleSpec = prototype.scale_columns
        self.handles_missing = prototype.handles_missing
        self.label_regime = prototype.label_regime
        self.supervised = prototype.supervised
        self.requires_entity = prototype.requires_entity
        self._prototype = prototype

        self._model: SentinelModel | None = None
        self._chosen: dict | None = None
        self._trace: list[dict] = []

    # --- Applicability ----------------------------------------------------

    def smallest_inner_positives(self, spec: DatasetSpec) -> float:
        """Positives expected in the thinnest inner validation slice.

        The first fold trains on one block of the development set, and a
        quarter of that becomes the slice candidates are ranked on. Estimated
        from declared fields rather than measured, because `applies_to` is
        answered before any data is loaded.
        """
        development = spec.expected_fraud * (1.0 - spec.holdout_fraction)
        first_fold_train = development / (spec.n_cv_folds + 1)
        return first_fold_train * self.inner_fraction

    def applies_to(self, spec: DatasetSpec) -> bool:
        """Refuse datasets too thin to rank candidates on.

        On creditcard this works out to roughly 20 positives in the slice, and
        a search scored on 20 positives selects noise — then reports it as a
        tuned model, which is worse than not tuning at all. Declining is the
        honest outcome, and it uses the same mechanism `requires_entity` does:
        the model states what it needs and the registry filters it out.
        """
        return (
            super().applies_to(spec)
            and self.smallest_inner_positives(spec) >= self.min_inner_positives
        )

    # --- Delegated declarations -------------------------------------------

    def select_features(self, available: list[str], spec: DatasetSpec) -> list[str]:
        return self._prototype.select_features(available, spec)

    def feature_groups(self) -> list[FeatureGroup] | None:
        return self._prototype.feature_groups()

    # --- Search -----------------------------------------------------------

    def _candidates(self) -> list[dict]:
        """A fixed random sample of the space.

        Seeded, so two runs draw the same candidates. Layer 8 pairs runs on
        identical rows and would otherwise be comparing two different searches
        as though they were two fits of one model.
        """
        rng = np.random.default_rng(self.seed)
        seen: set[tuple] = set()
        candidates: list[dict] = []

        # Sampling without replacement over a small grid: a duplicate draw is
        # wasted compute, not a different candidate.
        for _ in range(self.n_candidates * 20):
            if len(candidates) == self.n_candidates:
                break
            choice = {
                key: values[int(rng.integers(len(values)))]
                for key, values in self._space.items()
            }
            fingerprint = tuple(sorted(choice.items()))
            if fingerprint not in seen:
                seen.add(fingerprint)
                candidates.append(choice)
        return candidates

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "TunedModel":
        spec = self.spec
        _assert_time_ordered(X, spec)

        cut = int(len(X) * (1.0 - self.inner_fraction))
        inner_train, inner_val = X.iloc[:cut], X.iloc[cut:]
        y_train, y_val = y.iloc[:cut], y.iloc[cut:]

        positives = int(np.asarray(y_val).sum())
        if positives < self.min_inner_positives:
            raise TuningError(
                f"{self.name}: the inner validation slice holds {positives} "
                f"positives, below the {self.min_inner_positives} needed to rank "
                "candidates. Tuning on this fold would select on noise."
            )

        self._trace = []
        best_score, best_params = -np.inf, None

        for candidate in self._candidates():
            model = self._factory(**candidate).bind(spec)
            model.fit(inner_train, y_train)
            score = float(
                average_precision_score(y_val, model.risk_score(inner_val))
            )
            self._trace.append({"params": candidate, "inner_auprc": score})

            if score > best_score:
                best_score, best_params = score, candidate

        if best_params is None:
            raise TuningError(f"{self.name}: the search space produced no candidates")

        self._chosen = {**best_params, "inner_auprc": best_score, "n_inner_positives": positives}

        # Refit the winner on the whole training fold, inner slice included.
        # Selecting on a subset and then fitting on everything is the point:
        # the extra history is free, and withholding it would hand the untuned
        # baseline an advantage that has nothing to do with hyperparameters.
        self._model = self._factory(**best_params).bind(spec)
        self._model.fit(X, y)
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("fit() before risk_score()")
        return self._model.risk_score(X)

    def params(self) -> dict:
        """What was searched and what won.

        The runner builds a fresh model per fold, so the record shows the *last*
        fold's selection. `search_trace` is kept so a later fold's choice can be
        read back rather than inferred, and so a search that was nearly a tie
        cannot be reported as a decisive one.
        """
        return {
            "wraps": self._prototype.name,
            "n_candidates": self.n_candidates,
            "inner_fraction": self.inner_fraction,
            "seed": self.seed,
            "space": {key: list(values) for key, values in self._space.items()},
            "chosen": self._chosen,
            "search_trace": sorted(
                self._trace, key=lambda entry: -entry["inner_auprc"]
            )[:5],
        }
