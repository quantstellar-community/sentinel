"""Models that run on per-entity behavioural features.

Every model here is an estimator that already exists paired with a different
layer-4 declaration. That is the point: holding the estimator fixed and moving
only the feature space is what makes the difference between two runs
attributable to the features.

## What these are for

The anomaly layer measured nothing on creditcard — the hybrid moved −0.0064
across 0 of 4 folds — and the reason was structural rather than a tuning
failure. The anomaly component saw exactly the columns XGBoost already had, so
it had no information to contribute. `AMOUNT_Z_SCORE` and the velocity ratios
are the first columns in this project that the raw feature space does not
contain, because they are statements about an entity's own past rather than
about the transaction.

So the question these models exist to answer is not "is the autoencoder good"
but "does *normality per customer* carry signal that *normality overall* does
not". PIPELINE_V2 §14 experiment #5 is the sharpest form of it.

## Why the supervised pair keeps the weighted configuration

`xgboost_behavioral` matches `xgboost`, weighting included, even though
`xgboost_unweighted` measured better on IEEE-CIS across 6 of 6 folds. The
comparison it belongs to is `xgboost -> xgboost_behavioral`, and a pair that
changed the features *and* the class weighting at once would not attribute
either effect. The better configuration is a separate axis, already measured.
"""

from __future__ import annotations

from src.datasets import DatasetSpec
from src.features import (
    FeatureGroup,
    behavioral_column_names,
    behavioral_groups,
    structural_groups,
)
from src.models.anomaly import AutoencoderAnomaly, IsolationForestAnomaly
from src.models.hybrid import AnomalyAugmentedModel
from src.models.supervised import XGBoostBaseline


class BehaviouralFeatures:
    """Declares the entity feature groups and the dataset requirement they imply.

    `requires_entity` is what keeps these out of `models_for(creditcard)`.
    Without it they would run there, silently fall back to the structural
    pipeline — every behavioural group excludes itself when there is no entity —
    and produce a record named `xgboost_behavioral` holding a plain `xgboost`
    result. A model whose name misdescribes its record is worse than one that
    refuses to run.
    """

    requires_entity = True

    def feature_groups(self) -> list[FeatureGroup]:
        return structural_groups() + behavioral_groups()


class BehaviouralOnly(BehaviouralFeatures):
    """As above, but the model consumes only the behavioural columns.

    The pipeline still builds the structural columns, so this model and its
    non-`_only` counterpart run on an identical feature computation and differ
    purely in which subset reaches `fit`. That is what makes their paired
    comparison attribute the difference to the *raw columns* rather than to some
    incidental change in how the behavioural ones were produced.
    """

    def select_features(self, available: list[str], spec: DatasetSpec) -> list[str]:
        behavioural = set(behavioral_column_names())
        return [column for column in available if column in behavioural]


class XGBoostBehavioral(BehaviouralFeatures, XGBoostBaseline):
    """Experiment #2 — do behavioural features beat IEEE-CIS's own C/D blocks?

    The dataset already ships `C1`-`C14` (counting features) and `D1`-`D15`
    (timedeltas), which Vesta built for the same purpose. So this is not
    "features versus none" but "our per-entity features versus a vendor's", and
    a null result would be a real finding about the value of the entity proxy.
    """

    name = "xgboost_behavioral"


class XGBoostBehavioralOnly(BehaviouralOnly, XGBoostBaseline):
    """Experiment #3 — how much do the raw columns still add?

    26 columns against 458. If this lands close to the full model, most of the
    signal is behavioural; if it collapses, the raw blocks carry information the
    entity history does not reach.
    """

    name = "xgboost_behavioral_only"


class AutoencoderBehavioral(BehaviouralFeatures, AutoencoderAnomaly):
    """Experiment #4 — the project's central claim, in its testable form.

    On creditcard "normal" meant a global cloud of legitimate transactions and
    reconstruction error measured distance from it. With behavioural columns the
    same machinery measures distance from *this customer's* pattern: an amount
    40x their own average is far from normal even when it is unremarkable
    globally. Whether that reformulation helps is exactly what is unmeasured.
    """

    def __init__(self, **overrides):
        overrides.setdefault("name", "autoencoder_behavioral")
        super().__init__(**overrides)


class IsolationForestBehavioral(BehaviouralFeatures, IsolationForestAnomaly):
    """Control for the autoencoder above.

    The two react to training contamination in opposite directions — measured on
    creditcard, where the autoencoder lost 72% to a 0.17% fraud rate and the
    forest did not — so a behavioural gain that appears for only one of them says
    something about the objective function, not about the features.
    """

    def __init__(self, **overrides):
        overrides.setdefault("name", "isolation_forest_behavioral")
        super().__init__(**overrides)


class XGBoostHybridBehavioral(BehaviouralFeatures, AnomalyAugmentedModel):
    """Experiment #5 — has the anomaly layer earned its place yet?

    The same wrapper that measured nothing on creditcard, now with anomaly
    components that can see an entity's history. Its nested components inherit
    the behavioural columns automatically: they are fitted inside `fit`, on the
    frame the pipeline already produced.
    """

    def __init__(self, **overrides):
        overrides.setdefault("name", "xgboost_hybrid_behavioral")
        super().__init__(**overrides)


__all__ = [
    "AutoencoderBehavioral",
    "BehaviouralFeatures",
    "BehaviouralOnly",
    "IsolationForestBehavioral",
    "XGBoostBehavioral",
    "XGBoostBehavioralOnly",
    "XGBoostHybridBehavioral",
]
