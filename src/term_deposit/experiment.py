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

from term_deposit.metrics import evaluate
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


def fit_reference_model(frame: pd.DataFrame, seed: int = SEED):
    """The model this repository would actually propose: no leakage, evaluated in time.

    Returned fitted, along with its test set, so the CLI can draw the gains curve and
    read off coefficients without refitting.
    """
    train, test = temporal_split(frame)
    columns = feature_columns()
    model = build_models(seed=seed)["gradient_boosting"]
    model.fit(train[columns], target_vector(train))
    return model, test
