"""Rolling recalibration.

INSIGHTS.md §1.5 diagnoses the problem: the reference model ranks acceptably out of time
but predicts a mean of ~0.15 against an observed ~0.31, because the base rate moved
between the periods. This module is the treatment. Isotonic regression is fitted on the
most recent slice of the training period — the data a production system would have on
hand just before deployment — and applied to the test period.

Isotonic recalibration is monotone, so it changes the probability *level* while leaving
the ranking essentially intact (ties aside). It fixes the number the business multiplies
by deposit value; it cannot and does not improve who gets called.
"""

from __future__ import annotations

import pandas as pd
from sklearn.isotonic import IsotonicRegression

from term_deposit.experiment import REFERENCE_MODEL
from term_deposit.models import SEED, build_models
from term_deposit.preprocessing import feature_columns, target_vector
from term_deposit.splits import temporal_split

#: Share of the training period held back, at its most recent end, for recalibration.
CALIBRATION_WINDOW = 0.2


def recalibration_demo(
    frame: pd.DataFrame, seed: int = SEED
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (test target, raw scores, recalibrated scores) for the reference model.

    The training period is itself split in time: the model fits on the earlier part and
    the isotonic recalibrator on the most recent part, so nothing sees the test period.
    The same fitted model produces both score sets — the only difference is the isotonic
    map — so any gap between them is attributable to recalibration alone.
    """
    train, test = temporal_split(frame)
    model_period, calibration_period = temporal_split(train, test_fraction=CALIBRATION_WINDOW)

    columns = feature_columns()
    model = build_models(seed=seed)[REFERENCE_MODEL]
    model.fit(model_period[columns], target_vector(model_period))

    recalibrator = IsotonicRegression(out_of_bounds="clip")
    recalibrator.fit(
        model.predict_proba(calibration_period[columns])[:, 1],
        target_vector(calibration_period),
    )

    raw = pd.Series(model.predict_proba(test[columns])[:, 1], index=test.index)
    recalibrated = pd.Series(recalibrator.predict(raw), index=test.index)
    return target_vector(test), raw, recalibrated
