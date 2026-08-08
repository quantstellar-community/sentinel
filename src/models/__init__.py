"""Model registry.

Every entry is a *factory*, not an instance: the runner builds a fresh model for
each fold, so no state survives from one fold's training set into the next.

The registry is flat rather than nested per dataset. Applicability is a property
of the model, declared through `requires_entity` and checked by `applies_to()` —
the same mechanism feature groups use. Asking for a behavioural model on a
dataset with no entity information raises rather than silently degrading.
"""

from __future__ import annotations

from collections.abc import Callable

from src.datasets import DatasetSpec, get_spec
from src.models.anomaly import AutoencoderAnomaly, IsolationForestAnomaly
from src.models.base import AnomalyModel, ScaleSpec, SentinelModel, SklearnModel
from src.models.behavioral import (
    AutoencoderBehavioral,
    IsolationForestBehavioral,
    XGBoostBehavioral,
    XGBoostBehavioralOnly,
    XGBoostHybridBehavioral,
)
from src.models.hybrid import AnomalyAugmentedModel, iforest_only_hybrid
from src.models.pu import PUCascade, PUCascadeError
from src.models.regime import UNLABELED, LabelRegime
from src.models.supervised import (
    LightGBMBaseline,
    LogisticRegressionBaseline,
    XGBoostBaseline,
)
from src.models.tuning import (
    LIGHTGBM_SPACE,
    LOGREG_SPACE,
    XGBOOST_SPACE,
    TunedModel,
    TuningError,
)

ModelFactory = Callable[[], SentinelModel]

MODEL_REGISTRY: dict[str, ModelFactory] = {
    # ---------------------------------------------------------------- supervised
    # Phase 0 reference. Scales the dataset's declared default columns only —
    # on creditcard that is Time and Amount, which reproduces the recorded
    # baseline exactly.
    "logreg": LogisticRegressionBaseline,
    # Same estimator with every feature rescaled. Settled the open question in
    # docs/evaluation_protocol.md §6.2 by measurement: it changes nothing.
    "logreg_full_scale": lambda: LogisticRegressionBaseline(
        scale_columns="all", name="logreg_full_scale"
    ),
    "xgboost": XGBoostBaseline,
    "lightgbm": LightGBMBaseline,
    # docs/research_synthesis.md §2.2 recommends scale_pos_weight ~578 for both
    # boosting models. These drop it, so the recommendation is tested across all
    # folds rather than assumed.
    "xgboost_unweighted": lambda: XGBoostBaseline(balanced=False, name="xgboost_unweighted"),
    "lightgbm_unweighted": lambda: LightGBMBaseline(balanced=False, name="lightgbm_unweighted"),
    # ------------------------------------------------------------------ anomaly
    # Fit on the normal class alone. Expected to rank well below the supervised
    # models on this benchmark — see src/models/anomaly.py for why that is the
    # expected result rather than a failure.
    "isolation_forest": IsolationForestAnomaly,
    "autoencoder": AutoencoderAnomaly,
    # Checks the decision to drop the time column from anomaly inputs instead of
    # asserting it. See the module docstring in src/models/anomaly.py.
    "isolation_forest_with_time": lambda: IsolationForestAnomaly(
        keep_time=True, name="isolation_forest_with_time"
    ),
    # Measures whether reconstruction error needs every input on a comparable
    # scale, the same way logreg_full_scale did for the linear model.
    "autoencoder_minimal_scale": lambda: AutoencoderAnomaly(
        scale_columns="amount", name="autoencoder_minimal_scale"
    ),
    # ----------------------------------------------------- track C: label-blind
    # Same estimators as above, but trained on *everything* — undiscovered fraud
    # included — with no label information at all. The pair (B, C) measures what
    # knowing the training set is clean is worth.
    #
    # Prediction attached to that measurement: the gap should track training
    # contamination. On creditcard, at 0.17% fraud, it should be near zero; on
    # IEEE-CIS at 3.5% an autoencoder in track C must reconstruct fraud along
    # with the rest, so it should open up.
    "if_contaminated": lambda: IsolationForestAnomaly(
        name="if_contaminated", label_regime=UNLABELED
    ),
    "ae_contaminated": lambda: AutoencoderAnomaly(
        name="ae_contaminated", label_regime=UNLABELED
    ),
    # The only supervised model that never sees a label: an anomaly detector
    # manufactures the target it learns from. Its baseline is `if_contaminated` —
    # the same detector scored directly — because the question is whether
    # learning from a ranking beats using the ranking.
    "pu_cascade": PUCascade,
    # ------------------------------------------------------------------- hybrid
    # The combination step: anomaly score as evidence for a supervised decision
    # layer, not as a decision of its own.
    "xgboost_hybrid": AnomalyAugmentedModel,
    "xgboost_hybrid_iforest": iforest_only_hybrid,
    # -------------------------------------------------- behavioural (entity only)
    # Same estimators, per-entity feature space. These exclude themselves from
    # creditcard, which carries no customer identifier at all.
    #
    # Each answers one question from PIPELINE_V2 §14, and #5 is the one the
    # project's premise rests on: with columns describing an entity's own past,
    # does the anomaly layer finally contribute something the supervised model
    # did not already have?
    # -------------------------------------------------------------- tuned
    # Every model above runs on hand-set constants. These search instead, inside
    # each training fold, and exist to answer the question that leaves open:
    # how much of the gap between models is the algorithm and how much is the
    # configuration nobody looked at? One binary flag is already known to be
    # worth 10% relative on IEEE-CIS.
    "xgboost_tuned": lambda: TunedModel(
        XGBoostBaseline, XGBOOST_SPACE, name="xgboost_tuned"
    ),
    # The linear floor, tuned. Worth having because every "X beats logreg"
    # comparison in the project is measured against it: if the floor sits lower
    # than it needs to, those margins are all overstated by the same amount.
    # Exhaustive, not sampled: `LOGREG_SPACE` holds 14 points, and a sampled
    # subset of something that small is a needless source of doubt. The first
    # attempt drew 8 of 28 and missed `C=1.0` — the incumbent's setting — which
    # is exactly the failure a full sweep cannot have.
    #
    # Logistic regression converges slowly on 432 dense columns (a single fit on
    # the last fold takes minutes against XGBoost's ~30 seconds), so this is the
    # most expensive entry in the registry by wall-clock. It earns that by being
    # the linear floor every "X beats logreg" comparison is measured against.
    #
    # The factory bakes in `scale_columns="all"`, and that is load-bearing
    # rather than cosmetic. `TunedModel` inherits its scaling from the prototype
    # the factory builds, because the runner resolves preprocessing before `fit`
    # and a candidate cannot change it. Wrapping the plain baseline would
    # therefore lock the search at `"default"` — the setting already measured as
    # the *worse* of the two (`logreg` 0.1899 against `logreg_full_scale`
    # 0.2006). The search would then be tuning `C` on a handicap and losing to an
    # untuned entry for a reason having nothing to do with `C`.
    "logreg_tuned": lambda: TunedModel(
        lambda **overrides: LogisticRegressionBaseline(
            scale_columns="all", **overrides
        ),
        LOGREG_SPACE,
        name="logreg_tuned",
        n_candidates=14,
    ),
    "lightgbm_tuned": lambda: TunedModel(
        LightGBMBaseline, LIGHTGBM_SPACE, name="lightgbm_tuned"
    ),
    "xgboost_behavioral": XGBoostBehavioral,
    "xgboost_behavioral_only": XGBoostBehavioralOnly,
    "autoencoder_behavioral": AutoencoderBehavioral,
    "isolation_forest_behavioral": IsolationForestBehavioral,
    "xgboost_hybrid_behavioral": XGBoostHybridBehavioral,
}


def get_model(name: str, spec: DatasetSpec | str | None = None) -> SentinelModel:
    """Build a fresh model by registry name, bound to a dataset.

    Raises if the model needs entity information the dataset does not carry —
    better a clear failure than a behavioural model quietly running on nothing.
    """
    if name not in MODEL_REGISTRY:
        raise KeyError(f"unknown model {name!r}; available: {sorted(MODEL_REGISTRY)}")

    resolved = get_spec(spec)
    model = MODEL_REGISTRY[name]()
    if not model.applies_to(resolved):
        raise ValueError(
            f"model {name!r} requires entity information, which dataset "
            f"{resolved.name!r} does not declare (entity_keys is None)"
        )
    return model.bind(resolved)


def models_for(spec: DatasetSpec | str | None = None) -> list[str]:
    """Registry names that can run on the given dataset."""
    resolved = get_spec(spec)
    return sorted(
        name for name, factory in MODEL_REGISTRY.items() if factory().applies_to(resolved)
    )


def models_by_track(spec: DatasetSpec | str | None = None) -> dict[str, list[str]]:
    """Registry names grouped by label budget.

    The roster is organised along this axis rather than by algorithm: the same
    estimator under two regimes is two different experiments.
    """
    grouped: dict[str, list[str]] = {}
    for name in models_for(spec):
        grouped.setdefault(MODEL_REGISTRY[name]().track, []).append(name)
    return {track: sorted(names) for track, names in sorted(grouped.items())}


__all__ = [
    "MODEL_REGISTRY",
    "AnomalyAugmentedModel",
    "AnomalyModel",
    "AutoencoderAnomaly",
    "AutoencoderBehavioral",
    "IsolationForestAnomaly",
    "IsolationForestBehavioral",
    "XGBoostBehavioral",
    "XGBoostBehavioralOnly",
    "XGBoostHybridBehavioral",
    "LabelRegime",
    "LightGBMBaseline",
    "LogisticRegressionBaseline",
    "ScaleSpec",
    "LIGHTGBM_SPACE",
    "LOGREG_SPACE",
    "XGBOOST_SPACE",
    "PUCascade",
    "PUCascadeError",
    "SentinelModel",
    "SklearnModel",
    "TunedModel",
    "TuningError",
    "XGBoostBaseline",
    "get_model",
    "models_by_track",
    "models_for",
]
