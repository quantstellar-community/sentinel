"""Behavioural feature groups — what an entity's own past says about a row.

This is the layer the project's central claim rests on. Everywhere else, an
anomaly model looks at the same columns the supervised models already have, so
it has no information to contribute; that is why the anomaly layer measured
nothing on creditcard. These groups change that by encoding *this customer's
history* into the row, which turns "normal" from a global cloud of legitimate
transactions into something specific to the entity being scored.

Four groups, twenty-six columns, all functions of the entity's earlier rows:

    RollingWindows      12   activity inside trailing time windows
    VelocityRatios       7   short windows against long ones
    EntityHistory        6   expanding statistics over everything before now
    BenfordDeviation     1   leading-digit drift against Benford's law

All four are `derived`: they create signal rather than reshape it, so they are
opt-in and every result built on them is compared against one built without.

## The two primitives

Everything here reduces to a question about rows of the same entity, and there
are only two shapes of question:

    prior(v)        sum of v over this entity's rows *strictly before* this one
    window(v, w)    sum of v over this entity's rows in (t - w, t], this one included

Both are prefix-sum lookups over a single ordering, so the whole layer costs one
sort and a handful of linear passes rather than a groupby per feature.

## The trap this module exists to avoid

The intuitive spelling of "this entity's average amount" is wrong:

    df.groupby(entity)[amount].transform("mean")     # sees the entity's FUTURE

It pools every row of the entity, including ones that have not happened yet at
the moment being scored. Nothing raises, no test of the usual kind fails, and
every downstream number improves — which is what makes it dangerous. The
`prior`/`window` primitives above are the fix, applied uniformly: neither can
read an index past the row it is computing.
"""

from __future__ import annotations

import copy
from abc import abstractmethod

import numpy as np
import pandas as pd

from src.datasets import DatasetSpec
from src.features.base import FeatureError, FeatureGroup, NotFittedError

#: Guards every ratio in this module. Small enough not to move a real quotient,
#: large enough that a zero denominator yields a finite number instead of an inf
#: the model layer would have to reject.
EPSILON = 1e-5

#: Trailing windows, in real seconds. Converted into the time column's own units
#: through `spec.seconds_per_time_unit` — stating them in seconds here and
#: converting once is what keeps "24H" meaning a day on any dataset.
WINDOWS: dict[str, float] = {
    "1H": 3_600.0,
    "3H": 10_800.0,
    "24H": 86_400.0,
    "48H": 172_800.0,
    "7D": 604_800.0,
    "30D": 2_592_000.0,
}

#: Short window over long window. Reads as "how much of the last month's
#: activity happened in the last hour" — near 1.0 for a burst on a quiet
#: history, small for steady use.
RATIO_PAIRS: list[tuple[str, str]] = [("1H", "24H"), ("24H", "7D"), ("7D", "30D")]

SECONDS_PER_DAY = 86_400.0
SECONDS_PER_HOUR = 3_600.0

#: Hours counted as night for `HIST_NIGHT_RATIO`, as [start, end).
NIGHT_HOURS = (0, 5)

#: `DAYS_SINCE_LAST` when the entity has no earlier row. A sentinel rather than
#: NaN because here one direction is *correct*: never-seen-before should read as
#: "a very long time ago", and a median fill would say the opposite. The other
#: history columns have no such direction and use NaN — see `EntityHistory`.
NO_PRIOR_DAYS = 999.0

#: Below this many earlier transactions a leading-digit distribution is noise,
#: so `BENFORD_DEV` reports 0 rather than a large deviation that only reflects a
#: small sample.
BENFORD_MIN_HISTORY = 5

#: Benford's law: q_d = log10(1 + 1/d) for d = 1..9.
BENFORD_Q = np.log10(1.0 + 1.0 / np.arange(1, 10, dtype="float64"))


def leading_digit(amounts: np.ndarray) -> np.ndarray:
    """First significant decimal digit of each amount; 0 where undefined.

    Zero and negative amounts have no leading digit and are excluded from the
    Benford comparison rather than forced into a bucket.
    """
    digits = np.zeros(amounts.shape, dtype="int64")
    usable = amounts > 0
    if usable.any():
        magnitude = np.floor(np.log10(amounts[usable]))
        scaled = amounts[usable] / np.power(10.0, magnitude)
        # Rounding can push the quotient just past 10 (or just under 1); clip
        # rather than let a float artefact create a tenth digit.
        digits[usable] = np.clip(np.floor(scaled).astype("int64"), 1, 9)
    return digits


class _EntityView:
    """Rows regrouped so each entity is contiguous and internally time-ordered.

    The ordering is produced by `lexsort` on (entity, time, original position)
    rather than by relying on the caller to hand over a time-sorted frame. The
    third key makes ties deterministic, so two runs on the same data produce the
    same features — a precondition for the paired comparisons in layer 8.
    """

    def __init__(self, entity: pd.Series, times: np.ndarray, amounts: np.ndarray):
        codes = pd.factorize(entity, sort=False)[0]

        # factorize marks nulls -1, and -1 sorts ahead of every real code, so a
        # null identifier does not fail — it silently becomes one enormous
        # entity whose "history" is every unidentifiable row in the dataset.
        # That exact bug produced 60,416 transactions of history for a single
        # pseudo-customer before `DatasetSpec.entity_id` learned to fill missing
        # components. Loud is the only safe behaviour here.
        if (codes < 0).any():
            raise FeatureError(
                f"{int((codes < 0).sum()):,} rows carry no entity identifier. "
                "Behavioural features would pool them into one entity. Fix the "
                "identifier (see DatasetSpec.entity_id) rather than the symptom."
            )

        self.n = len(codes)
        position = np.arange(self.n)

        # lexsort takes the primary key last.
        self.order = np.lexsort((position, times, codes))
        self.codes = codes[self.order]
        self.times = times[self.order]
        self.amounts = amounts[self.order]

        # Index of the first row of each entity's block, broadcast to every row.
        # Group starts increase along the array, so a running maximum over
        # "my index if I start a block, else 0" propagates each one forward.
        starts_here = np.ones(self.n, dtype=bool)
        starts_here[1:] = self.codes[1:] != self.codes[:-1]
        self.group_start = np.maximum.accumulate(
            np.where(starts_here, np.arange(self.n), 0)
        )

        #: How many rows this entity has strictly before each row.
        self.prior_count = np.arange(self.n) - self.group_start

    def restore(self, values: np.ndarray) -> np.ndarray:
        """Undo the entity ordering, returning values in the input row order."""
        out = np.empty_like(values)
        out[self.order] = values
        return out

    def prior_sum(self, values: np.ndarray) -> np.ndarray:
        """Sum of `values` over this entity's rows strictly before each row."""
        cumulative = np.concatenate([[0.0], np.cumsum(values)])
        return cumulative[np.arange(self.n)] - cumulative[self.group_start]

    def previous(self, values: np.ndarray) -> np.ndarray:
        """`values` at this entity's immediately preceding row; NaN if none."""
        out = np.full(self.n, np.nan)
        has_prior = self.prior_count > 0
        out[has_prior] = values[np.arange(self.n)[has_prior] - 1]
        return out

    def window_start(self, span: float) -> np.ndarray:
        """First index of the same entity with time > t - span, per row.

        Searching a structured array keyed on (entity, time) is what confines
        the result to the entity's own block: a target reaching back past the
        entity's first row still compares greater than every row of the previous
        entity, so it lands on that first row. The clamp that a plain
        time-only search would need is a property of the key instead of a line
        of code that could be forgotten.
        """
        dtype = np.dtype([("entity", self.codes.dtype), ("time", self.times.dtype)])

        keys = np.empty(self.n, dtype=dtype)
        keys["entity"], keys["time"] = self.codes, self.times

        targets = np.empty(self.n, dtype=dtype)
        targets["entity"], targets["time"] = self.codes, self.times - span

        return np.searchsorted(keys, targets, side="right")

    def window_sum(self, values: np.ndarray, span: float) -> np.ndarray:
        """Sum of `values` over (t - span, t], current row included."""
        cumulative = np.concatenate([[0.0], np.cumsum(values)])
        return cumulative[np.arange(self.n) + 1] - cumulative[self.window_start(span)]

    def window_count(self, span: float) -> np.ndarray:
        """Number of this entity's rows in (t - span, t], current row included."""
        return (np.arange(self.n) + 1 - self.window_start(span)).astype("float64")


class EntityFeatureGroup(FeatureGroup):
    """Base for groups whose columns are a function of an entity's own past.

    ## Why `fit` keeps the training rows

    A group is handed one frame at a time. Left at that, `transform(val)` would
    restart every entity's history at the first validation row: a customer with
    fifty transactions behind them would look new, and `HIST_TXN_COUNT` would
    mean "rows since this evaluation block began" rather than "rows this
    customer has". Training and validation rows would then carry *different
    quantities under the same column name* — a train/serve skew that would make
    the behavioural layer look worthless for a reason that has nothing to do
    with whether behaviour predicts fraud.

    So `fit` stores the entity, time and amount of every training row, and
    `transform` prepends the ones that happened before the frame it is given.

    ## Why that is not leakage

    Two independent reasons, either of which would be enough:

    * `fit` receives the training fold and nothing else, so the stored history
      cannot contain an evaluation row.
    * Only history *strictly earlier* than the frame's first timestamp is used,
      so information still moves one way.

    The strictly-earlier rule also makes the group self-consistent. Calling
    `transform(train)` right after `fit(train)` finds nothing to prepend — no
    training row precedes the training frame's own start — so the same history
    cannot be counted twice.

    A frame overlapping the stored history in time keeps only the part before
    it, which understates history rather than inventing it. Wrong in the safe
    direction, and it cannot arise from the runner, whose splits never overlap.
    """

    requires_entity = True
    derived = True

    def __init__(self) -> None:
        self._spec: DatasetSpec | None = None
        self._history: pd.DataFrame | None = None

    # --- Contract ---------------------------------------------------------

    @property
    def spec(self) -> DatasetSpec:
        if self._spec is None:
            raise NotFittedError(f"{self.name}: fit() first")
        return self._spec

    def fit(self, train: pd.DataFrame, spec: DatasetSpec) -> "EntityFeatureGroup":
        self._spec = spec
        self._history = self._minimal(train, spec)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        view, n_prepended = self._view(df)
        computed = self._compute(view)

        out = {
            name: view.restore(values)[n_prepended:] for name, values in computed.items()
        }
        return pd.DataFrame(out, index=df.index)[self.output_columns()]

    @abstractmethod
    def _compute(self, view: _EntityView) -> dict[str, np.ndarray]:
        """Columns for every row of `view`, in the view's own ordering."""

    @abstractmethod
    def column_names(self) -> list[str]:
        """This group's columns. Static — no fit required.

        The names come from the window and ratio tables rather than from the
        data, which is what lets a model declare "behavioural columns only"
        before any frame exists. `output_columns` is the same list behind the
        layer-4 fit check.
        """

    def output_columns(self) -> list[str]:
        if self._spec is None:
            raise NotFittedError(f"{self.name}: fit() first")
        return self.column_names()

    # --- History carry-over ------------------------------------------------

    @staticmethod
    def _minimal(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
        """The three columns every group here needs, and nothing else.

        Keeping the whole training frame would hold a 400-column table alive for
        the sake of three of them.
        """
        return pd.DataFrame(
            {
                "entity": spec.entity_id(df).to_numpy(),
                "time": df[spec.time_column].to_numpy(dtype="float64"),
                "amount": df[spec.amount_column].to_numpy(dtype="float64"),
            }
        )

    def _view(self, df: pd.DataFrame) -> tuple[_EntityView, int]:
        """A view over (earlier history + `df`), and how many rows were prepended."""
        if self._history is None:
            raise NotFittedError(f"{self.name}: fit() first")

        current = self._minimal(df, self.spec)
        earlier = (
            self._history[self._history["time"] < current["time"].min()]
            if len(current)
            else self._history.iloc[:0]
        )

        combined = pd.concat([earlier, current], ignore_index=True)
        view = _EntityView(
            combined["entity"],
            combined["time"].to_numpy(),
            combined["amount"].to_numpy(),
        )
        return view, len(earlier)

    def narrowed_to(self, entities) -> "EntityFeatureGroup":
        """A copy whose stored history keeps only the listed entities.

        Shallow-copied so the original keeps its full history: an experiment may
        still be using the pipeline this was narrowed from.
        """
        if self._history is None:
            return self

        clone = copy.copy(self)
        clone._history = self._history[self._history["entity"].isin(list(entities))]
        return clone

    # --- Units -------------------------------------------------------------

    def _span(self, seconds: float) -> float:
        """A real-time span expressed in the time column's units."""
        return seconds / self.spec.seconds_per_time_unit

    def _hour_of_day(self, times: np.ndarray) -> np.ndarray:
        seconds = times * self.spec.seconds_per_time_unit
        return (seconds % SECONDS_PER_DAY) / SECONDS_PER_HOUR


class RollingWindows(EntityFeatureGroup):
    """Amount and transaction count inside six trailing windows. 12 columns.

    Safe by construction: a trailing window only looks backwards, so there is no
    version of this group that could see the future. It is the raw material the
    velocity ratios are built from.
    """

    name = "rolling_windows"

    def _compute(self, view: _EntityView) -> dict[str, np.ndarray]:
        out: dict[str, np.ndarray] = {}
        for label, seconds in WINDOWS.items():
            span = self._span(seconds)
            out[f"SUM_AMOUNT_{label}"] = view.window_sum(view.amounts, span)
            out[f"COUNT_{label}"] = view.window_count(span)
        return out

    def column_names(self) -> list[str]:
        return [f"SUM_AMOUNT_{label}" for label in WINDOWS] + [
            f"COUNT_{label}" for label in WINDOWS
        ]


class VelocityRatios(EntityFeatureGroup):
    """Short windows against long ones — bursts, not volume. 7 columns.

    A ratio near 1.0 says an entity's whole month of activity happened inside
    the shorter window; steady use gives roughly the ratio of the two window
    lengths. That normalisation is the point: it compares a customer against
    themselves, so a heavy spender and a light one are on the same scale.

    Recomputes the windows rather than reading `RollingWindows`' output. A group
    only ever sees the raw frame, and threading one group's columns into another
    would couple them into a single unit that could no longer be enabled,
    measured, or removed on its own. The cost is one extra pass over an
    already-cheap prefix sum.
    """

    name = "velocity_ratios"

    def _compute(self, view: _EntityView) -> dict[str, np.ndarray]:
        needed = {label for pair in RATIO_PAIRS for label in pair} | {"30D"}
        sums, counts = {}, {}
        for label in needed:
            span = self._span(WINDOWS[label])
            sums[label] = view.window_sum(view.amounts, span)
            counts[label] = view.window_count(span)

        out: dict[str, np.ndarray] = {}
        for short, long in RATIO_PAIRS:
            out[f"VELOCITY_AMOUNT_{short}_VS_{long}"] = sums[short] / (
                sums[long] + EPSILON
            )
        for short, long in RATIO_PAIRS:
            out[f"VELOCITY_COUNT_{short}_VS_{long}"] = counts[short] / (
                counts[long] + EPSILON
            )

        average_30d = sums["30D"] / (counts["30D"] + EPSILON)
        out["AMOUNT_VS_30D_AVG_RATIO"] = view.amounts / (average_30d + EPSILON)
        return out

    def column_names(self) -> list[str]:
        return (
            [f"VELOCITY_AMOUNT_{a}_VS_{b}" for a, b in RATIO_PAIRS]
            + [f"VELOCITY_COUNT_{a}_VS_{b}" for a, b in RATIO_PAIRS]
            + ["AMOUNT_VS_30D_AVG_RATIO"]
        )


class EntityHistory(EntityFeatureGroup):
    """Expanding statistics over everything the entity did before now. 6 columns.

    Every column here is *strictly prior* — the row being scored is excluded
    from its own history. That is the stronger reading of "what did we know
    about this entity before this transaction", and it is what makes
    `AMOUNT_Z_SCORE` mean anything: with the current amount inside its own
    denominator, a single large transaction would partly cancel itself out.

    ## Absence is encoded two different ways, on purpose

    `DAYS_SINCE_LAST` uses the sentinel 999 because "no earlier transaction" has
    a correct direction — it should read as a long time ago. The remaining
    history columns use NaN, because no value of "this entity's average amount"
    is the right answer when the entity has no amounts yet. The runner already
    resolves both: tree models read NaN natively, and models that cannot get a
    median fill. Choosing a number here would be asserting a fact that is not
    known.

    `ENTITY_IS_SINGLETON` marks exactly those rows, which is what lets a model
    tell "typical" apart from "no evidence". Without it the velocity ratios are
    actively misleading: an entity with one transaction has every ratio at
    1.0 — not because its behaviour is steady but because it has no history.
    """

    name = "entity_history"

    def _compute(self, view: _EntityView) -> dict[str, np.ndarray]:
        prior_count = view.prior_count.astype("float64")
        has_prior = prior_count > 0
        unknown = np.full(view.n, np.nan)

        prior_amount = view.prior_sum(view.amounts)
        average = np.divide(prior_amount, prior_count, out=unknown.copy(), where=has_prior)

        hour = self._hour_of_day(view.times)
        night_start, night_end = NIGHT_HOURS
        at_night = ((hour >= night_start) & (hour < night_end)).astype("float64")
        night_ratio = np.divide(
            view.prior_sum(at_night), prior_count, out=unknown.copy(), where=has_prior
        )

        elapsed = (view.times - view.previous(view.times)) * self.spec.seconds_per_time_unit
        days_since = np.where(has_prior, elapsed / SECONDS_PER_DAY, NO_PRIOR_DAYS)

        return {
            "HIST_TXN_COUNT": prior_count,
            "HIST_AVG_AMOUNT": average,
            "AMOUNT_Z_SCORE": view.amounts / (average + EPSILON),
            "HIST_NIGHT_RATIO": night_ratio,
            "DAYS_SINCE_LAST": days_since,
            "ENTITY_IS_SINGLETON": (~has_prior).astype("float64"),
        }

    def column_names(self) -> list[str]:
        return [
            "HIST_TXN_COUNT",
            "HIST_AVG_AMOUNT",
            "AMOUNT_Z_SCORE",
            "HIST_NIGHT_RATIO",
            "DAYS_SINCE_LAST",
            "ENTITY_IS_SINGLETON",
        ]


class BenfordDeviation(EntityFeatureGroup):
    """How far the entity's leading digits drift from Benford's law. 1 column.

        BENFORD_DEV = sum_d p_d * ln(p_d / q_d),   q_d = log10(1 + 1/d)

    where p_d is measured over the entity's earlier transactions only. The
    premise is that naturally occurring amounts follow the law and fabricated or
    machine-generated ones need not; the KL divergence is the standard way to
    score that, and it is directional — it charges for mass the entity puts
    where Benford puts little.

    Entities with fewer than five earlier transactions score 0. At that size the
    divergence measures the sample, not the entity, and letting it through would
    dress up 39.5% of IEEE-CIS groups as anomalous for having short histories.
    """

    name = "benford_deviation"

    def _compute(self, view: _EntityView) -> dict[str, np.ndarray]:
        digits = leading_digit(view.amounts)

        prior = np.stack(
            [view.prior_sum((digits == d).astype("float64")) for d in range(1, 10)]
        )
        total = prior.sum(axis=0)
        observed = np.divide(
            prior, total, out=np.zeros_like(prior), where=(total > 0)
        )

        # 0 * ln(0) is 0 in the limit; only the digits actually seen contribute.
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(
                observed > 0, observed * np.log(observed / BENFORD_Q[:, None]), 0.0
            )

        return {
            "BENFORD_DEV": np.where(total >= BENFORD_MIN_HISTORY, terms.sum(axis=0), 0.0)
        }

    def column_names(self) -> list[str]:
        return ["BENFORD_DEV"]
