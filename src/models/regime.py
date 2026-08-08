"""Layer 5 — Label Regime: the gate controlling how much label a model sees.

Without this layer the line between "supervised" and "unsupervised" is mush.
Take a concrete case: an anomaly model trained on the normal class alone — is
that unsupervised?

No. It **uses labels to filter the training set**; it just keeps them out of the
loss. That is one-class semi-supervised. A genuinely label-blind model trains on
*everything*, undiscovered fraud included, and never learns which rows those
were.

Those three situations differ in kind and produce different results. Making them
an explicit layer turns the difference into something measurable:

    A - B   the value of fraud labels inside the loss function
    B - C   the value of knowing the training set is clean

And the second has a testable prediction attached: B - C should depend on how
contaminated training is. On creditcard, at 0.17% fraud, contamination is
negligible and B should sit near C. On IEEE-CIS at 3.5% an autoencoder in track
C must reconstruct fraud along with everything else, so the gap should open.

**The invariant that makes any of this meaningful:** true labels are used at
evaluation regardless of what the model saw during fitting. This layer only
controls what reaches `fit`. Track C is therefore a measurement rather than a
guess — run it blind, score it against the truth.

Track C is not an academic exercise either. Three operational conditions
produce exactly it: chargeback labels arrive 30-90 days late, undetected fraud
is permanently labelled legitimate, and a new deployment starts with no labels
at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class LabelRegimeError(ValueError):
    """Raised when a model and a regime cannot be combined honestly."""


class LabelRegime(ABC):
    """Controls the label information entering `fit`."""

    name: str = "unnamed"

    #: "A" fully supervised · "B" one-class · "C" label-blind
    track: str = "?"

    #: Whether the regime uses labels to *filter* the training rows. Distinct
    #: from putting them in the loss, which is what track A does.
    filters_to_normal: bool = False

    #: Whether any label information at all reaches the model.
    sees_labels: bool = True

    @abstractmethod
    def apply(self, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        """Return the `(X, y)` the model is permitted to see when fitting."""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "track": self.track,
            "sees_labels": self.sees_labels,
            "filters_to_normal": self.filters_to_normal,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{type(self).__name__}(track={self.track!r})"


class FullySupervised(LabelRegime):
    """Track A — every label, straight into the loss."""

    name = "fully_supervised"
    track = "A"
    sees_labels = True
    filters_to_normal = False

    def apply(self, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        return X, y


class OneClass(LabelRegime):
    """Track B — labels filter the training set, but stay out of the loss.

    The model sees only the normal class. This consumes label information at
    the filtering step, which is why it is semi-supervised rather than
    unsupervised: someone had to know which rows were fraud in order to remove
    them.
    """

    name = "one_class"
    track = "B"
    sees_labels = True
    filters_to_normal = True

    def apply(self, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        normal = np.asarray(y) == 0
        if not normal.any():
            raise LabelRegimeError("one-class regime: no normal rows to fit on")
        return X[normal], y[normal]


class Unlabeled(LabelRegime):
    """Track C — no label information reaches the model at all.

    Training keeps its real fraud contamination. The labels handed to `fit` are
    a constant zero: not a claim that nothing is fraud, but a placeholder that
    carries no information, so a model which peeked at `y` would learn nothing
    from it.

    A supervised model cannot run here — with a constant target there is
    nothing to fit. The runner rejects that combination rather than letting it
    train on a degenerate label vector and produce a number.
    """

    name = "unlabeled"
    track = "C"
    sees_labels = False
    filters_to_normal = False

    def apply(self, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        blind = pd.Series(0, index=y.index, name=y.name, dtype="int64")
        return X, blind


class PartialLabel(LabelRegime):
    """Between A and C — only a fraction of the fraud is revealed.

    A quantitative model of label lag: sweep `reveal_fraction` from 0 to 1 and
    the resulting curve answers "how much labelling is enough". Hidden fraud is
    marked legitimate, which is what unlabelled fraud looks like in production.
    """

    track = "A/C"
    filters_to_normal = False
    sees_labels = True

    def __init__(self, reveal_fraction: float, seed: int = 42):
        if not 0.0 <= reveal_fraction <= 1.0:
            raise LabelRegimeError(f"reveal_fraction must be in [0, 1], got {reveal_fraction}")
        self.reveal_fraction = reveal_fraction
        self.seed = seed
        self.name = f"partial_label_{reveal_fraction:.2f}"

    def apply(self, X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
        positives = np.flatnonzero(np.asarray(y) == 1)
        n_reveal = int(round(len(positives) * self.reveal_fraction))

        rng = np.random.default_rng(self.seed)
        revealed = rng.choice(positives, size=n_reveal, replace=False) if n_reveal else []

        blinded = pd.Series(0, index=y.index, name=y.name, dtype="int64")
        blinded.iloc[list(revealed)] = 1
        return X, blinded

    def describe(self) -> dict:
        return {**super().describe(), "reveal_fraction": self.reveal_fraction, "seed": self.seed}


#: Shared instances — regimes are stateless, so one of each is enough.
FULLY_SUPERVISED = FullySupervised()
ONE_CLASS = OneClass()
UNLABELED = Unlabeled()

TRACKS = {"A": FULLY_SUPERVISED, "B": ONE_CLASS, "C": UNLABELED}
