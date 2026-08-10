"""Evaluation.

Accuracy is deliberately absent: predicting "no" for every customer scores 88.3% on this
data while producing zero business value. What a campaign actually needs is a *ranking* —
given capacity for k calls, how many subscribers do those k calls reach — so precision@k
and its lift over the base rate are the headline numbers, with PR-AUC summarising the
ranking across all cut-offs.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

#: Call-list sizes worth reporting, as a fraction of the contactable population. These
#: stand in for "how many agent-hours do we have this week".
DEFAULT_K_FRACTIONS = (0.05, 0.10, 0.20)

#: Ties are broken by a fixed shuffle rather than by row order. A model that scores every
#: customer identically — the prior baseline does exactly this — would otherwise be ranked
#: by position in the CSV, which here is contact date, and would score against the
#: drifting subscription rate instead of against chance.
TIE_BREAK_SEED = 0


def _ranked_indices(scores: np.ndarray) -> np.ndarray:
    """Customer indices from most to least likely to subscribe, ties shuffled."""
    scores = np.asarray(scores)
    shuffled = np.random.default_rng(TIE_BREAK_SEED).permutation(len(scores))
    return shuffled[np.argsort(-scores[shuffled], kind="stable")]


def _top_k_mask(scores: np.ndarray, k_fraction: float) -> np.ndarray:
    if not 0 < k_fraction <= 1:
        raise ValueError(f"k_fraction must be in (0, 1], got {k_fraction}")
    scores = np.asarray(scores)
    k = max(1, round(len(scores) * k_fraction))

    mask = np.zeros(len(scores), dtype=bool)
    mask[_ranked_indices(scores)[:k]] = True
    return mask


def gains_curve(y_true, scores) -> tuple[np.ndarray, np.ndarray]:
    """Share of the list called against share of all subscribers reached.

    The campaign-planning view: "if we work down the ranked list, how much of the
    available value have we captured by the time we stop?"
    """
    y_true = np.asarray(y_true)
    captured = np.cumsum(y_true[_ranked_indices(scores)]) / y_true.sum()
    called = np.arange(1, len(y_true) + 1) / len(y_true)
    return called, captured


def precision_at_k(y_true, scores, k_fraction: float) -> float:
    """Share of the top-scoring k_fraction of customers who actually subscribed."""
    return float(np.asarray(y_true)[_top_k_mask(scores, k_fraction)].mean())


def lift_at_k(y_true, scores, k_fraction: float) -> float:
    """How many times better than calling a random k_fraction of the list."""
    return precision_at_k(y_true, scores, k_fraction) / float(np.asarray(y_true).mean())


def evaluate(y_true, scores, k_fractions=DEFAULT_K_FRACTIONS) -> dict[str, float]:
    """Summarise a set of predicted probabilities."""
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)

    results = {
        "base_rate": float(y_true.mean()),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        # Calibration matters here because the base rate moves so much between periods:
        # a model can rank well and still tell the business the wrong number.
        "brier": float(brier_score_loss(y_true, scores)),
        "mean_predicted": float(scores.mean()),
    }
    for fraction in k_fractions:
        label = f"{fraction:.0%}"
        results[f"precision@{label}"] = precision_at_k(y_true, scores, fraction)
        results[f"lift@{label}"] = lift_at_k(y_true, scores, fraction)
    return results
