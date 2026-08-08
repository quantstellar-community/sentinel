"""Layer 4 tests for the behavioural groups.

These features are the ones worth distrusting. A leak here does not raise, does
not fail a shape check, and improves every downstream number — the failure mode
this project has already documented twice. So the tests are built around the
properties that a peeking implementation could not satisfy, rather than around
the values a correct one happens to produce:

1.  Deleting later rows must not change an earlier row's features.
2.  Features computed across a fit/transform boundary must equal the ones a
    single pass over the joined frame would give. That is what makes the history
    carry-over correct rather than merely well-intentioned.
3.  Transforming the training frame must not replay its own stored history.
4.  One entity's rows must not affect another's.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.datasets import CREDITCARD, IEEECIS
from src.evaluation import runner
from src.features import (
    BENFORD_MIN_HISTORY,
    NO_PRIOR_DAYS,
    WINDOWS,
    BenfordDeviation,
    EntityHistory,
    FeaturePipeline,
    NotFittedError,
    RollingWindows,
    VelocityRatios,
    behavioral_column_names,
    behavioral_groups,
    behavioral_pipeline,
    default_pipeline,
    leading_digit,
    structural_groups,
)
from src.models import XGBoostBehavioral, get_model, models_for

HOUR = 3_600.0
DAY = 86_400.0

GROUPS = [RollingWindows, VelocityRatios, EntityHistory, BenfordDeviation]
GROUP_IDS = [g.name for g in GROUPS]


def spread_frame(n: int = 400, n_entities: int = 25, seed: int = 0) -> pd.DataFrame:
    """An IEEE-shaped frame whose timestamps span weeks rather than seconds.

    The conftest generator packs every row into a few hundred seconds, which
    would put all six windows on top of each other and hide any window bug.
    """
    rng = np.random.default_rng(seed)
    times = np.sort(rng.uniform(0.0, 45 * DAY, size=n))
    entity = rng.integers(0, n_entities, size=n)

    return pd.DataFrame(
        {
            "TransactionID": np.arange(n),
            "TransactionDT": times,
            "TransactionAmt": rng.exponential(80.0, size=n) + 1.0,
            "card1": entity.astype(float),
            "card2": np.zeros(n),
            "addr1": np.zeros(n),
            "isFraud": (rng.random(n) < 0.05).astype(int),
        }
    )


def one_entity(times: list[float], amounts: list[float]) -> pd.DataFrame:
    """A single entity's timeline, for checking arithmetic by hand."""
    n = len(times)
    return pd.DataFrame(
        {
            "TransactionID": np.arange(n),
            "TransactionDT": np.asarray(times, dtype=float),
            "TransactionAmt": np.asarray(amounts, dtype=float),
            "card1": np.ones(n),
            "card2": np.zeros(n),
            "addr1": np.zeros(n),
            "isFraud": np.zeros(n, dtype=int),
        }
    )


# --------------------------------------------------------------------------
# 1. Nothing may read forward
# --------------------------------------------------------------------------


@pytest.mark.parametrize("group_class", GROUPS, ids=GROUP_IDS)
def test_deleting_later_rows_leaves_earlier_features_unchanged(group_class):
    """The leakage test that means something.

    Not "was fit given the training fold" — an implementation that peeks passes
    that trivially. What must hold is that the future is not an input.
    """
    df = spread_frame()
    group = group_class().fit(df.iloc[:200], IEEECIS)

    full = group.transform(df.iloc[:200])
    truncated = group.transform(df.iloc[:150])

    pd.testing.assert_frame_equal(full.iloc[:150], truncated)


def test_history_average_is_not_the_entity_wide_mean():
    """Guards the specific trap in PIPELINE_V2 §6.

        df.groupby(entity)[amount].transform("mean")

    pools every row of the entity, including ones that have not happened yet.
    It raises nothing and makes every metric look better, so the only thing
    standing between it and a published result is a test that names it.
    """
    df = one_entity(times=[0.0, HOUR], amounts=[10.0, 1_000.0])
    out = EntityHistory().fit(df, IEEECIS).transform(df)

    pooled_mean = df["TransactionAmt"].mean()  # 505.0 — what the wrong spelling gives
    assert np.isnan(out["HIST_AVG_AMOUNT"].iloc[0]), "the first row has no history at all"
    assert out["HIST_AVG_AMOUNT"].iloc[1] == 10.0, "only the earlier row may count"
    assert out["HIST_AVG_AMOUNT"].iloc[1] != pooled_mean


def test_benford_uses_only_earlier_rows():
    """Same trap, second site. An entity whose amounts switch leading digit
    partway through must not have the later digits colour the earlier rows."""
    amounts = [1.0] * 6 + [900.0] * 6
    df = one_entity(times=[i * HOUR for i in range(12)], amounts=amounts)
    out = BenfordDeviation().fit(df, IEEECIS).transform(df)["BENFORD_DEV"]

    # Row 6 is the first with a full history of leading-1 amounts, and Benford
    # puts 30.1% of its mass on digit 1, so an all-1 history is a real deviation.
    assert out.iloc[6] == pytest.approx(np.log(1.0 / np.log10(2.0)), rel=1e-9)
    assert out.iloc[6] > 0


# --------------------------------------------------------------------------
# 2. The history carry-over
# --------------------------------------------------------------------------


@pytest.mark.parametrize("group_class", GROUPS, ids=GROUP_IDS)
def test_features_across_a_split_match_a_single_pass_over_the_joined_frame(group_class):
    """The property the carry-over exists to provide.

    Without it, a validation row would restart its entity's history at the fold
    boundary: the same column name would carry "activity since this block began"
    on one side and "activity of this customer" on the other. This asserts the
    two sides agree.
    """
    df = spread_frame(n=500)
    train, validation = df.iloc[:300], df.iloc[300:]

    across_the_split = group_class().fit(train, IEEECIS).transform(validation)
    in_one_pass = group_class().fit(df, IEEECIS).transform(df).iloc[300:]

    pd.testing.assert_frame_equal(across_the_split, in_one_pass)


def test_a_validation_row_keeps_the_history_its_entity_built_in_training():
    """The concrete consequence: a returning customer is not treated as new."""
    train = one_entity(times=[0.0, HOUR, 2 * HOUR], amounts=[10.0, 20.0, 30.0])
    validation = one_entity(times=[3 * HOUR], amounts=[100.0])

    out = EntityHistory().fit(train, IEEECIS).transform(validation)

    assert out["HIST_TXN_COUNT"].iloc[0] == 3
    assert out["HIST_AVG_AMOUNT"].iloc[0] == 20.0
    assert out["ENTITY_IS_SINGLETON"].iloc[0] == 0.0


def test_transforming_the_training_frame_does_not_replay_its_own_history():
    """`fit` stores the training rows, so transforming that same frame is the
    one call that could count them twice. The strictly-earlier filter is what
    prevents it, and this is what would catch its removal."""
    train = spread_frame(n=300)
    out = EntityHistory().fit(train, IEEECIS).transform(train)

    first_appearance = ~IEEECIS.entity_id(train).duplicated()
    assert (out.loc[first_appearance.to_numpy(), "HIST_TXN_COUNT"] == 0).all(), (
        "an entity's first training row was given a history — the stored frame "
        "was replayed into its own source"
    )


# --------------------------------------------------------------------------
# 3. Entities do not bleed into each other
# --------------------------------------------------------------------------


def test_one_entitys_rows_do_not_reach_another():
    df = spread_frame(n=300, n_entities=8)
    reference = EntityHistory().fit(df, IEEECIS).transform(df)

    # Drop every row of one entity; the others must be untouched.
    entity = IEEECIS.entity_id(df)
    victim = entity.iloc[0]
    survivors = df[(entity != victim).to_numpy()]

    without = EntityHistory().fit(survivors, IEEECIS).transform(survivors)
    pd.testing.assert_frame_equal(without, reference.loc[survivors.index])


def test_windows_are_confined_to_the_entity_and_left_open():
    """Boundary semantics, stated rather than assumed.

    The window is (t - w, t]: a transaction exactly one hour old has left the
    1H window. PIPELINE_V2 §6 writes the closed form [t - w, t]; this is the
    half-open reading, which is the one that makes consecutive windows partition
    time without double-counting.
    """
    df = one_entity(times=[0.0, HOUR, 2 * HOUR], amounts=[100.0, 200.0, 300.0])
    out = RollingWindows().fit(df, IEEECIS).transform(df)

    assert out["COUNT_1H"].tolist() == [1.0, 1.0, 1.0], "the row an hour back is excluded"
    assert out["COUNT_24H"].tolist() == [1.0, 2.0, 3.0]
    assert out["SUM_AMOUNT_24H"].tolist() == [100.0, 300.0, 600.0]


# --------------------------------------------------------------------------
# 4. Absence, and how it is encoded
# --------------------------------------------------------------------------


def test_an_entitys_first_row_reports_no_history_rather_than_a_guess():
    df = one_entity(times=[0.0], amounts=[42.0])
    out = EntityHistory().fit(df, IEEECIS).transform(df)

    assert out["HIST_TXN_COUNT"].iloc[0] == 0
    assert out["ENTITY_IS_SINGLETON"].iloc[0] == 1.0
    assert np.isnan(out["HIST_AVG_AMOUNT"].iloc[0]), "no average exists yet"
    assert np.isnan(out["HIST_NIGHT_RATIO"].iloc[0])
    assert out["DAYS_SINCE_LAST"].iloc[0] == NO_PRIOR_DAYS, (
        "recency is the one column where absence has a correct direction"
    )


def test_singleton_flag_separates_steady_from_unknown():
    """Every velocity ratio of a first-ever transaction is 1.0 — not because
    behaviour is steady but because there is no history. The flag is what lets a
    model tell the two apart."""
    df = one_entity(times=[0.0], amounts=[42.0])

    ratios = VelocityRatios().fit(df, IEEECIS).transform(df)
    flag = EntityHistory().fit(df, IEEECIS).transform(df)["ENTITY_IS_SINGLETON"]

    assert ratios["VELOCITY_COUNT_1H_VS_24H"].iloc[0] == pytest.approx(1.0, abs=1e-4)
    assert flag.iloc[0] == 1.0


def test_benford_is_silent_until_the_history_is_long_enough():
    """Below five earlier transactions the divergence measures the sample, not
    the entity — and it would mark 39.5% of IEEE-CIS groups as anomalous for
    being short."""
    df = one_entity(
        times=[i * HOUR for i in range(8)], amounts=[1.0] * 8
    )
    out = BenfordDeviation().fit(df, IEEECIS).transform(df)["BENFORD_DEV"]

    assert (out.iloc[:BENFORD_MIN_HISTORY] == 0.0).all()
    assert out.iloc[BENFORD_MIN_HISTORY] > 0.0


def test_leading_digit_ignores_amounts_that_have_none():
    digits = leading_digit(np.array([0.0, -5.0, 1.0, 9.99, 100.0, 0.042, 999.999]))
    assert digits.tolist() == [0, 0, 1, 9, 1, 4, 9]


# --------------------------------------------------------------------------
# 5. Composition with the rest of layer 4
# --------------------------------------------------------------------------


def test_behavioural_groups_exclude_themselves_from_a_dataset_without_entities():
    """creditcard carries no customer identifier, so the pipeline must fall back
    to the structural one rather than fail or invent an entity."""
    pipeline = behavioral_pipeline(CREDITCARD)

    assert [g.name for g in pipeline.groups] == [g.name for g in structural_groups()]
    assert sorted(pipeline.skipped) == sorted(g.name for g in behavioral_groups())


def test_behavioural_pipeline_adds_exactly_twenty_six_columns():
    df = spread_frame()
    structural = default_pipeline(IEEECIS).fit(df).output_columns()
    full = behavioral_pipeline(IEEECIS).fit(df).output_columns()

    added = [c for c in full if c not in structural]
    assert len(added) == 26
    assert added == behavioral_column_names()


def test_column_names_are_available_before_fit():
    """A model has to declare "behavioural columns only" against a feature space
    that does not exist yet, so the names cannot depend on having seen data."""
    assert len(behavioral_column_names()) == 26
    assert "AMOUNT_Z_SCORE" in behavioral_column_names()
    assert all(f"SUM_AMOUNT_{w}" in behavioral_column_names() for w in WINDOWS)


@pytest.mark.parametrize("group_class", GROUPS, ids=GROUP_IDS)
def test_output_columns_before_fit_raises(group_class):
    with pytest.raises(NotFittedError):
        group_class().output_columns()


@pytest.mark.parametrize("group_class", GROUPS, ids=GROUP_IDS)
def test_every_behavioural_group_is_declared_derived(group_class):
    """Derived groups change the feature space and therefore every downstream
    number, so none of them may ride along in the default pipeline."""
    assert group_class().derived is True
    assert group_class().requires_entity is True
    assert group_class.name not in [g.name for g in structural_groups()]


def test_behavioural_columns_carry_no_infinities():
    """Every ratio here divides by a quantity that can be zero. The epsilon
    guard is what keeps the model layer from having to reject the row."""
    df = spread_frame(n=400)
    out = FeaturePipeline(behavioral_groups(), IEEECIS).fit(df).transform(df)

    assert not np.isinf(out.to_numpy(dtype="float64")).any()


# --------------------------------------------------------------------------
# 6. Layer 6 declares the pipeline, layer 7 obeys it
# --------------------------------------------------------------------------


def test_a_model_without_a_declaration_still_gets_the_structural_default():
    """The migration constraint depends on this. Every recorded creditcard
    result was produced by the default pipeline, so a model that declares
    nothing must keep getting exactly that."""
    model = get_model("xgboost", CREDITCARD)

    assert model.feature_groups() is None
    assert [g.name for g in runner.pipeline_for(model, CREDITCARD).groups] == [
        g.name for g in structural_groups()
    ]


def test_a_behavioural_model_gets_its_declared_groups():
    model = get_model("xgboost_behavioral", IEEECIS)
    names = [g.name for g in runner.pipeline_for(model, IEEECIS).groups]

    assert names == [g.name for g in structural_groups() + behavioral_groups()]


def test_an_explicit_pipeline_argument_outranks_the_declaration():
    """One-off experiments have to be able to override, or a question like
    "what does this model do on only these columns" needs a registry entry."""
    override = default_pipeline(IEEECIS)
    model = get_model("xgboost_behavioral", IEEECIS)

    assert runner.pipeline_for(model, IEEECIS, override) is override


def test_each_fold_gets_a_pipeline_of_its_own():
    """Groups hold fitted state — an encoder vocabulary, an entity's stored
    history. Sharing one pipeline across folds would let fold 3's training set
    reach fold 1 through a group that failed to fully reset."""
    model = get_model("xgboost_behavioral", IEEECIS)
    first = runner.pipeline_for(model, IEEECIS)
    second = runner.pipeline_for(model, IEEECIS)

    assert first is not second
    assert first.groups[-1] is not second.groups[-1]


def test_behavioural_models_refuse_a_dataset_with_no_entities():
    """Silently degrading would be worse than failing: every behavioural group
    excludes itself when there is no entity, so the run would succeed and write
    a record named `xgboost_behavioral` holding a plain `xgboost` result."""
    for name in ("xgboost_behavioral", "autoencoder_behavioral"):
        assert name not in models_for(CREDITCARD)
        with pytest.raises(ValueError, match="requires entity information"):
            get_model(name, CREDITCARD)


def test_behavioural_only_consumes_exactly_the_behavioural_columns():
    df = spread_frame()
    available = behavioral_pipeline(IEEECIS).fit(df).output_columns()

    chosen = get_model("xgboost_behavioral_only", IEEECIS).select_features(
        available, IEEECIS
    )

    assert sorted(chosen) == sorted(behavioral_column_names())
    assert len(chosen) == 26


def test_the_declared_pipeline_is_still_fitted_on_the_training_fold_only():
    """Letting the model choose the groups must not move where they are fitted.
    A behavioural group that saw the evaluation fold at fit time would leak
    through its stored history."""
    seen: list[int] = []

    class Spy(RollingWindows):
        name = "spy_rolling"

        def fit(self, train, spec):
            seen.append(len(train))
            return super().fit(train, spec)

    class SpyModel(XGBoostBehavioral):
        name = "spy_model"

        def feature_groups(self):
            return [*structural_groups(), Spy()]

    dev = spread_frame(n=600)
    record = runner.run_cv(SpyModel, spec=IEEECIS, dev=dev, n_bootstrap=0, n_folds=2)

    assert len(seen) == 2, "one fit per fold"
    assert all(n < len(dev) for n in seen), "a fit saw the whole development set"
    assert seen == sorted(seen), "the expanding window must grow, not shuffle"
    assert record.feature_pipeline["groups"][-1]["name"] == "spy_rolling"


def test_features_are_deterministic_across_runs():
    """Paired comparison in layer 8 assumes two runs on the same data produce
    the same features; tie-breaking by original position is what guarantees it
    when several transactions share a timestamp."""
    df = spread_frame(n=300)
    df.loc[df.index[:50], "TransactionDT"] = 0.0  # force a large tie group

    first = behavioral_pipeline(IEEECIS).fit(df).transform(df)
    second = behavioral_pipeline(IEEECIS).fit(df).transform(df)

    pd.testing.assert_frame_equal(first, second)
