import numpy as np
import pytest

from term_deposit.metrics import evaluate, lift_at_k, precision_at_k

# 20 customers, 4 of whom subscribe: a 20% base rate.
Y_TRUE = np.array([1, 1, 1, 1] + [0] * 16)
PERFECT = np.linspace(1.0, 0.0, 20)
REVERSED = np.linspace(0.0, 1.0, 20)


def test_perfect_ranking_puts_every_subscriber_in_the_top_20_percent():
    assert precision_at_k(Y_TRUE, PERFECT, 0.20) == 1.0


def test_worst_ranking_finds_nobody():
    assert precision_at_k(Y_TRUE, REVERSED, 0.20) == 0.0


def test_calling_everyone_just_returns_the_base_rate():
    assert precision_at_k(Y_TRUE, PERFECT, 1.0) == pytest.approx(0.20)


def test_lift_is_precision_relative_to_the_base_rate():
    assert lift_at_k(Y_TRUE, PERFECT, 0.20) == pytest.approx(1.0 / 0.20)


def test_lift_of_one_means_no_better_than_random():
    assert lift_at_k(Y_TRUE, PERFECT, 1.0) == pytest.approx(1.0)


def test_a_constant_score_cannot_beat_the_base_rate():
    """Ties must not be resolved by row order.

    The prior baseline scores every customer identically. Ranking those ties by position
    would score it against the dataset's ordering — which is contact date, along which
    the subscription rate drifts — rather than against chance.
    """
    ordered_by_outcome = np.array([1] * 200 + [0] * 800)  # positives first, as in a sorted file
    constant = np.full(1000, 0.5)
    assert precision_at_k(ordered_by_outcome, constant, 0.20) == pytest.approx(0.20, abs=0.05)


def test_tie_breaking_is_deterministic():
    constant = np.full(1000, 0.5)
    y = np.array([1] * 200 + [0] * 800)
    assert precision_at_k(y, constant, 0.20) == precision_at_k(y, constant, 0.20)


def test_k_fraction_outside_the_unit_interval_is_rejected():
    for bad in (0, 1.5, -0.1):
        with pytest.raises(ValueError, match="k_fraction"):
            precision_at_k(Y_TRUE, PERFECT, bad)


def test_evaluate_reports_ranking_and_calibration_together():
    results = evaluate(Y_TRUE, PERFECT)
    assert results["roc_auc"] == 1.0
    assert results["base_rate"] == pytest.approx(0.20)
    assert results["precision@20%"] == 1.0
    assert "brier" in results and "mean_predicted" in results


def test_evaluate_covers_every_requested_call_list_size():
    results = evaluate(Y_TRUE, PERFECT, k_fractions=(0.05, 0.5))
    assert {"precision@5%", "lift@5%", "precision@50%", "lift@50%"} <= set(results)
