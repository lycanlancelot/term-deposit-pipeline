"""The year reconstruction is load-bearing: every temporal claim depends on it."""

import pandas as pd
import pytest

from term_deposit.data import add_campaign_date, recover_campaign_year


def test_year_advances_on_each_backwards_step():
    months = pd.Series(["may", "dec", "jan", "jun", "dec", "feb"])
    assert list(recover_campaign_year(months, start_year=2008)) == [
        2008, 2008, 2009, 2009, 2009, 2010
    ]


def test_year_does_not_advance_on_a_repeated_month():
    months = pd.Series(["may", "may", "may", "jun"])
    assert list(recover_campaign_year(months, start_year=2008)) == [2008] * 4


def test_unrecognised_month_is_rejected_rather_than_silently_dropped():
    with pytest.raises(ValueError, match="unrecognised month names"):
        recover_campaign_year(pd.Series(["may", "smarch"]))


def test_day_level_disorder_within_a_month_is_rejected():
    """Rows out of order inside one month break the ordering assumption."""
    frame = pd.DataFrame({"month": ["may", "may"], "day": [10, 2], "y": ["no", "no"]})
    with pytest.raises(ValueError, match="not chronological"):
        add_campaign_date(frame)


def test_month_level_disorder_is_indistinguishable_from_a_rollover():
    """A known limitation, asserted so it stays visible.

    A backwards month step is *defined* as a year boundary, so genuinely shuffled data
    is silently "recovered" as spanning more years instead of raising. The guard in
    `add_campaign_date` cannot catch this; only the agreement between the recovered span
    and the dataset's published date range tells us the assumption holds here.
    """
    frame = pd.DataFrame({"month": ["jun", "may"], "day": [1, 2], "y": ["no", "no"]})
    recovered = add_campaign_date(frame)
    assert list(recovered.campaign_year) == [2008, 2009]


def test_recovered_span_matches_the_published_description(dated):
    """The dataset is documented as running May 2008 to November 2010.

    Nothing in the rollover-counting method forces that range, so agreement is
    independent evidence that the reconstruction is right.
    """
    assert dated.campaign_date.min() == pd.Timestamp("2008-05-05")
    assert dated.campaign_date.max() == pd.Timestamp("2010-11-17")
    assert dated.campaign_date.is_monotonic_increasing
