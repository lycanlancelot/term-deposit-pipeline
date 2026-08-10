"""A temporal split that leaks is worse than no temporal split, because it looks fine."""

import pytest

from term_deposit.splits import random_split, temporal_split


def test_no_test_row_predates_any_training_row(dated):
    train, test = temporal_split(dated)
    assert train.campaign_date.max() < test.campaign_date.min()


def test_a_single_day_never_straddles_the_boundary(dated):
    train, test = temporal_split(dated)
    assert not set(train.campaign_date) & set(test.campaign_date)


def test_split_covers_every_row_exactly_once(dated):
    train, test = temporal_split(dated)
    assert len(train) + len(test) == len(dated)
    assert not set(train.index) & set(test.index)


def test_test_fraction_is_approximately_honoured(dated):
    _, test = temporal_split(dated, test_fraction=0.2)
    assert 0.15 < len(test) / len(dated) < 0.25


def test_invalid_fraction_is_rejected(dated):
    with pytest.raises(ValueError, match="between 0 and 1"):
        temporal_split(dated, test_fraction=1.5)


def test_random_split_preserves_the_target_rate(dated):
    train, test = random_split(dated)
    assert train.y.eq("yes").mean() == pytest.approx(test.y.eq("yes").mean(), abs=0.005)


def test_random_split_is_reproducible(dated):
    first, _ = random_split(dated, seed=7)
    second, _ = random_split(dated, seed=7)
    assert first.index.equals(second.index)
