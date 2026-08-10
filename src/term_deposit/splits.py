"""Train/test splitting strategies.

Two are provided on purpose. The out-of-time split is the honest one for data that
drifts this much; the random split is kept so the optimism it buys can be reported as a
number instead of asserted.
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split

from term_deposit.data import TARGET

DEFAULT_TEST_FRACTION = 0.2
DEFAULT_SEED = 42


def temporal_split(
    frame: pd.DataFrame,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    date_column: str = "campaign_date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on the earlier campaigns, test on the most recent ones.

    The boundary is a *date*, not a row position, so a single day never straddles the
    split — otherwise calls made on the same day by the same agents would appear in both
    sets. That makes the realised test fraction approximate; the cutoff date is the
    thing worth reporting.
    """
    if not 0 < test_fraction < 1:
        raise ValueError(f"test_fraction must be between 0 and 1, got {test_fraction}")

    ordered = frame.sort_values(date_column, kind="stable")
    cutoff = ordered[date_column].iloc[int(len(ordered) * (1 - test_fraction))]

    train = ordered[ordered[date_column] < cutoff]
    test = ordered[ordered[date_column] >= cutoff]
    if train.empty or test.empty:
        raise ValueError(f"cutoff {cutoff} leaves one side of the split empty")
    return train, test


def random_split(
    frame: pd.DataFrame,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    seed: int = DEFAULT_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified random split — the conventional choice, and the optimistic one here."""
    return train_test_split(
        frame, test_size=test_fraction, random_state=seed, stratify=frame[TARGET]
    )
