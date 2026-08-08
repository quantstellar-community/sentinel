"""Track C cascade: manufacture labels from an anomaly score, then learn from them.

The last model in the label-budget roster and the only one that is supervised
without being shown a single label. An anomaly detector ranks the training fold,
the extremes of that ranking become pseudo-labels, and a supervised model learns
from those. The real labels reappear at layer 8 exactly as they do for every
other model.

## The question this answers, and the one it does not

It answers: *does a supervised model trained on anomaly-derived pseudo-labels
generalise better than the anomaly score it was derived from?* There is a real
mechanism for a gain — the supervised model sees the whole feature space at once
and can smooth a boundary the detector drew from random partitions — and a real
mechanism for a loss, since it can only ever approximate a teacher that is
itself weak.

The honest baseline is therefore `if_contaminated`, the same detector scored
directly. Comparing a cascade against a *supervised* model would be measuring
the label budget, which layer 5 already measures.

## Where the prior knowledge enters

`assumed_positive_rate` is the crux, and `history.md` §32 caught the trap in the
design this replaces: setting `contamination=0.03`, flagging the top 3%,
learning that 3%, then thresholding at the 97th percentile reproduces 3%. The
alert rate came out because it went in.

So the rate is a **declared prior**, not a discovery. In a cold start it is
whatever the operator believes or can afford to review, and nothing in this
class estimates it. Setting it from the observed fraud rate would be label
knowledge entering through the back door, which is why the registry default is a
round operational number rather than IEEE-CIS's 3.5%.

## Three things deliberately not implemented

`history.md` §32 examined each on the way to rejecting it:

* **Elkan-Noto calibration.** The correction divides by a global constant, so it
  is a monotone transform and cannot move a rank-based metric at all. Its
  `min(·, 1.0)` clamp does have an effect, and a harmful one: every sample above
  the constant collapses to exactly 1.0, producing the tied-block failure that
  `score_resolution_warning` exists to catch.
* **nnPU.** A specific risk estimator with a class prior and a non-negativity
  correction. Nothing here implements it, so nothing here claims it.
* **Cross-validated uncertainty removal.** Dropping the highest-loss samples
  discards the hardest and most informative cases — on this problem, exactly the
  fraud worth catching.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.data.preprocessor import Preprocessor
from src.models.anomaly import IsolationForestAnomaly
from src.models.base import ScaleSpec, SentinelModel
from src.models.regime import UNLABELED
from src.models.supervised import XGBoostBaseline


class PUCascadeError(RuntimeError):
    """Raised when the bootstrap cannot produce a trainable label vector."""


class PUCascade(SentinelModel):
    """Anomaly bootstrap into a supervised learner, with no labels at any point.

    The middle of the anomaly ranking is thrown away rather than called
    negative. Rows just below the flagging threshold are where undiscovered
    fraud concentrates, so labelling them legitimate would teach the supervised
    model that the detector's near-misses are safe — training it to reproduce
    the detector's mistakes rather than its judgements.
    """

    name = "pu_cascade"
    scale_columns: ScaleSpec = "none"  # the outer model is a tree ensemble
    handles_missing = True             # ...which reads NaN natively
    supervised = True
    label_regime = UNLABELED
    generates_own_labels = True

    def __init__(
        self,
        *,
        name: str | None = None,
        assumed_positive_rate: float = 0.05,
        reliable_negative_fraction: float = 0.50,
        anomaly_factory: Callable[[], SentinelModel] = IsolationForestAnomaly,
        supervised_factory: Callable[[], SentinelModel] = XGBoostBaseline,
    ):
        if name:
            self.name = name
        if not 0.0 < assumed_positive_rate < 1.0:
            raise PUCascadeError("assumed_positive_rate must be in (0, 1)")
        if not 0.0 < reliable_negative_fraction < 1.0:
            raise PUCascadeError("reliable_negative_fraction must be in (0, 1)")
        if assumed_positive_rate + reliable_negative_fraction > 1.0:
            raise PUCascadeError(
                "the flagged head and the reliable tail overlap; there would be "
                "no discarded band and rows would carry both labels"
            )

        self.assumed_positive_rate = assumed_positive_rate
        self.reliable_negative_fraction = reliable_negative_fraction
        self._anomaly_factory = anomaly_factory
        self._supervised_factory = supervised_factory

        self._anomaly: SentinelModel | None = None
        self._preprocessor: Preprocessor | None = None
        self._anomaly_columns: list[str] = []
        self._supervised: SentinelModel | None = None
        #: Manufactured labels for the training fold, kept so a diagnostic can
        #: score them against the truth the model itself never saw.
        self.pseudo_labels: np.ndarray | None = None

    # --- Bootstrap ---------------------------------------------------------

    def _anomaly_scores(self, X: pd.DataFrame, fit: bool = False) -> np.ndarray:
        """Anomaly score per row, with the component's own preprocessing.

        The component declares its own scaling and missing-value handling, and
        handing it the outer model's frame would silently override both.
        """
        if fit:
            spec = self.spec
            component = self._anomaly_factory().bind(spec)
            columns = component.select_features(list(X.columns), spec)
            scale_columns = component.resolve_scale_columns(columns, spec)

            preprocessor = None
            if scale_columns or not component.handles_missing:
                preprocessor = Preprocessor(
                    columns=scale_columns, impute=not component.handles_missing
                ).fit(X)

            frame = preprocessor.transform(X) if preprocessor is not None else X
            # No label filtering: this is track C, so the detector trains on
            # everything, undiscovered fraud included.
            component.fit(frame[columns], pd.Series(0, index=X.index))

            self._anomaly = component
            self._preprocessor = preprocessor
            self._anomaly_columns = columns

        if self._anomaly is None:
            raise PUCascadeError("the anomaly component was never fitted")

        frame = (
            self._preprocessor.transform(X) if self._preprocessor is not None else X
        )
        return np.asarray(self._anomaly.risk_score(frame[self._anomaly_columns]))

    def _bootstrap(self, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Turn a ranking into (labels, mask of rows to train on).

        Quantiles rather than a fixed score: an anomaly score has no calibrated
        scale, so the only meaningful threshold is positional.
        """
        n = scores.size
        flagged = np.quantile(scores, 1.0 - self.assumed_positive_rate)
        trusted = np.quantile(scores, self.reliable_negative_fraction)

        labels = np.zeros(n, dtype="int64")
        labels[scores >= flagged] = 1
        keep = (scores >= flagged) | (scores <= trusted)

        n_positive = int(labels[keep].sum())
        if n_positive == 0 or n_positive == int(keep.sum()):
            raise PUCascadeError(
                f"{self.name}: the bootstrap produced {n_positive} pseudo-positives "
                f"out of {int(keep.sum())} training rows — a constant target. The "
                "anomaly scores are probably degenerate; check the detector first."
            )
        return labels, keep

    # --- Core --------------------------------------------------------------

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "PUCascade":
        """`y` arrives as a constant zero from the unlabeled regime and is unused.

        Checked rather than assumed: if a real label vector ever reached here,
        the model would be quietly supervised while still reporting track C.
        """
        if int(np.asarray(y).sum()) != 0:
            raise PUCascadeError(
                f"{self.name} received {int(np.asarray(y).sum())} positive labels. "
                "It declares the unlabeled regime and must not be given any."
            )

        scores = self._anomaly_scores(X, fit=True)
        labels, keep = self._bootstrap(scores)
        self.pseudo_labels = labels

        self._supervised = self._supervised_factory().bind(self.spec)
        self._supervised.fit(X[keep], pd.Series(labels[keep], index=X.index[keep]))
        return self

    def risk_score(self, X: pd.DataFrame) -> np.ndarray:
        if self._supervised is None:
            raise RuntimeError("fit() before risk_score()")
        return self._supervised.risk_score(X)

    def params(self) -> dict:
        return {
            "assumed_positive_rate": self.assumed_positive_rate,
            "reliable_negative_fraction": self.reliable_negative_fraction,
            "discarded_band": round(
                1.0 - self.assumed_positive_rate - self.reliable_negative_fraction, 4
            ),
            "anomaly": self._anomaly_factory().name,
            "supervised": self._supervised_factory().name,
        }


__all__ = ["PUCascade", "PUCascadeError"]
