import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score

from term_deposit.calibration import recalibration_demo


def test_recalibration_moves_the_level_without_touching_the_ranking(dated):
    test_y, raw, recalibrated = recalibration_demo(dated)

    # The level: the recalibrated mean must land closer to the observed rate.
    observed = test_y.mean()
    assert abs(recalibrated.mean() - observed) < abs(raw.mean() - observed)

    # The ranking: isotonic is monotone, so AUC may only shift by tie formation.
    assert roc_auc_score(test_y, recalibrated) > roc_auc_score(test_y, raw) - 0.02

    # And it should not cost accuracy of the probabilities themselves.
    assert brier_score_loss(test_y, recalibrated) < brier_score_loss(test_y, raw)


def test_recalibrated_scores_are_valid_probabilities(dated):
    _, _, recalibrated = recalibration_demo(dated)
    assert np.isfinite(recalibrated).all()
    assert ((recalibrated >= 0) & (recalibrated <= 1)).all()
