"""The estimators under comparison.

Three, spanning the useful range: a prior baseline that proves the metrics are honest, a
linear model that can be read, and a gradient booster that handles the long tails and
interactions without being asked. Defaults are kept almost everywhere — the exercise
explicitly does not reward tuning, and an untuned pair still answers "is there signal
here, and how much of it is linear".
"""

from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from term_deposit.preprocessing import build_preprocessor

SEED = 42


def build_models(include_duration: bool = False, seed: int = SEED) -> dict[str, Pipeline]:
    """Model name to an unfitted pipeline that takes the raw feature frame.

    Preprocessing is bundled into each pipeline so that cross-validation or a refit
    cannot accidentally learn scaling statistics from data the model should not have
    seen.

    Note on class weighting: the target is 11.7% positive, and the reflex is
    `class_weight="balanced"`. It is left off deliberately. Reweighting barely moves a
    *ranking* — which is what precision@k and PR-AUC measure — while badly inflating the
    predicted probabilities, and calibrated probabilities are what turn a ranking into an
    expected value per call. Since the campaign decision is "rank customers, call down
    the list until capacity runs out" rather than "threshold at 0.5", ranking plus
    calibration is worth more than a balanced decision boundary we would not use.
    """

    def with_preprocessing(estimator) -> Pipeline:
        return Pipeline(
            [
                ("features", build_preprocessor(include_duration)),
                ("estimator", estimator),
            ]
        )

    return {
        # Predicts the training base rate for everyone. Any model that cannot beat this
        # on a ranking metric has found nothing.
        "prior": with_preprocessing(DummyClassifier(strategy="prior")),
        "logistic_regression": with_preprocessing(
            LogisticRegression(max_iter=1000, random_state=seed)
        ),
        "gradient_boosting": with_preprocessing(
            HistGradientBoostingClassifier(random_state=seed)
        ),
    }
