"""The evaluation grid.

Every model is run under both split strategies and both feature sets. That is more runs
than a single headline number needs, but the comparisons are the point: the gap between
splits measures how much optimism a random split buys, and the gap between feature sets
measures what excluding `duration` costs. Both are claims this repository makes, so both
are computed rather than asserted.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from term_deposit.metrics import bootstrap_ci, bootstrap_delta_ci, evaluate
from term_deposit.models import SEED, build_models
from term_deposit.preprocessing import feature_columns, target_vector
from term_deposit.splits import random_split, temporal_split

SplitStrategy = Callable[[pd.DataFrame], tuple[pd.DataFrame, pd.DataFrame]]

SPLIT_STRATEGIES: dict[str, SplitStrategy] = {
    "temporal": temporal_split,
    "random": random_split,
}


def run_grid(frame: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Fit every (split, model, feature set) combination and score it on held-out data."""
    rows = []
    for split_name, split in SPLIT_STRATEGIES.items():
        train, test = split(frame)
        for include_duration in (False, True):
            columns = feature_columns(include_duration)
            train_x, train_y = train[columns], target_vector(train)
            test_x, test_y = test[columns], target_vector(test)

            for model_name, model in build_models(include_duration, seed).items():
                scores = model.fit(train_x, train_y).predict_proba(test_x)[:, 1]
                rows.append(
                    {
                        "split": split_name,
                        "model": model_name,
                        "features": "with duration" if include_duration else "no duration",
                        "n_train": len(train),
                        "n_test": len(test),
                        **evaluate(test_y, scores),
                    }
                )
    return pd.DataFrame(rows)


def reference_comparison(frame: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    """Can the honest evaluation actually tell logistic regression and GBM apart?

    Both are fitted on the temporal split without `duration`, then compared with a
    *paired* bootstrap — the same resamples score both models, so the interval reflects
    the difference rather than test-set volatility. This is the evidence behind the
    reference-model choice in `fit_reference_model`.
    """
    train, test = temporal_split(frame)
    columns = feature_columns()
    train_y, test_y = target_vector(train), target_vector(test)

    scores = {}
    for name in ("logistic_regression", "gradient_boosting"):
        model = build_models(seed=seed)[name]
        scores[name] = model.fit(train[columns], train_y).predict_proba(test[columns])[:, 1]

    rows = []
    for metric_name, metric in (("roc_auc", roc_auc_score), ("pr_auc", average_precision_score)):
        row = {"metric": metric_name}
        for name, model_scores in scores.items():
            row[name] = metric(test_y, model_scores)
            row[f"{name}_ci"] = bootstrap_ci(test_y, model_scores, metric)
        row["delta_ci"] = bootstrap_delta_ci(
            test_y, scores["logistic_regression"], scores["gradient_boosting"], metric
        )
        rows.append(row)
    return pd.DataFrame(rows)


#: Chosen on the evidence from `reference_comparison`: out of time, logistic regression
#: is statistically indistinguishable from gradient boosting on ROC-AUC (paired delta CI
#: covers zero) and significantly better on PR-AUC. A tie breaks toward the model whose
#: coefficients can be read, explained and challenged.
REFERENCE_MODEL = "logistic_regression"


def fit_reference_model(frame: pd.DataFrame, seed: int = SEED):
    """The model this repository would actually propose: no leakage, evaluated in time.

    Returned fitted, along with its test set, so the CLI can draw the gains curve and
    read off coefficients without refitting.
    """
    train, test = temporal_split(frame)
    columns = feature_columns()
    model = build_models(seed=seed)[REFERENCE_MODEL]
    model.fit(train[columns], target_vector(train))
    return model, test
