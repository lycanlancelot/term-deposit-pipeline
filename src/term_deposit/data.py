"""Loading the campaign export and reconstructing its time axis.

The raw file records a month name but no year. The rows are ordered by contact date,
so every backwards step in the month sequence marks a year boundary — counting those
rollovers recovers the calendar year, which is what makes an out-of-time evaluation
possible. See PLAN.md for why that matters.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_MONTH_TO_NUMBER = {name: number for number, name in enumerate(MONTHS, start=1)}

TARGET = "y"

#: Known only after the call it describes, so it cannot inform who to call.
#: Quarantined rather than deleted so its cost can be measured — see preprocessing.
LEAKY_COLUMNS = ("duration",)

#: The campaign is documented as starting in May 2008.
FIRST_CAMPAIGN_YEAR = 2008

_REQUIRED_COLUMNS = frozenset({TARGET, "month", "day"})


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read the semicolon-delimited campaign export."""
    frame = pd.read_csv(path, sep=";")
    missing = _REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing expected columns: {sorted(missing)}")
    return frame


def recover_campaign_year(month: pd.Series, start_year: int = FIRST_CAMPAIGN_YEAR) -> pd.Series:
    """Reconstruct the calendar year from a chronologically ordered month sequence.

    Assumes the rows are in contact-date order — the year advances each time the month
    goes backwards. Raises on month names outside the known set rather than silently
    producing NaN.

    Limitation: a backwards month step is *defined* as a year boundary, so this cannot
    tell a real rollover from rows that are simply out of order. The assumption is
    checked externally, by the recovered span agreeing with the dataset's documented
    May 2008 - Nov 2010 range.
    """
    number = month.map(_MONTH_TO_NUMBER)
    unknown = sorted(set(month[number.isna()]))
    if unknown:
        raise ValueError(f"unrecognised month names: {unknown}")

    rolled_over = number.diff() < 0
    return (start_year + rolled_over.cumsum()).astype(int).rename("campaign_year")


def add_campaign_date(
    frame: pd.DataFrame, start_year: int = FIRST_CAMPAIGN_YEAR
) -> pd.DataFrame:
    """Return a copy with `campaign_year` and `campaign_date` columns.

    Partially validates the reconstruction: if the recovered dates are not chronological
    then the ordering assumption does not hold and every downstream temporal split would
    be quietly wrong. This catches disorder *within* a month only — see the limitation
    noted on `recover_campaign_year`.
    """
    year = recover_campaign_year(frame["month"], start_year)
    date = pd.to_datetime(
        {"year": year, "month": frame["month"].map(_MONTH_TO_NUMBER), "day": frame["day"]}
    )
    if not date.is_monotonic_increasing:
        raise ValueError(
            "recovered campaign dates are not chronological; the rows are not in "
            "contact-date order, so the year cannot be recovered this way"
        )
    return frame.assign(campaign_year=year, campaign_date=date)
