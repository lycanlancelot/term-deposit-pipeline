import pytest

from term_deposit.power import required_sample_size


def test_the_number_quoted_in_insights_is_reproducible():
    """A +10% relative lift on this dataset's 11.7% base rate."""
    assert required_sample_size(0.117, 0.10) == 12354


def test_detecting_a_smaller_effect_costs_more_customers():
    assert required_sample_size(0.117, 0.10) > required_sample_size(0.117, 0.30)


def test_a_higher_base_rate_needs_fewer_customers():
    """The recent campaign period converts at 31%, which is much cheaper to test on."""
    assert required_sample_size(0.311, 0.10) < required_sample_size(0.117, 0.10)


def test_more_power_costs_more_customers():
    assert required_sample_size(0.117, 0.20, power=0.95) > required_sample_size(
        0.117, 0.20, power=0.80
    )


def test_impossible_or_meaningless_inputs_are_rejected():
    with pytest.raises(ValueError, match="baseline_rate"):
        required_sample_size(0, 0.1)
    with pytest.raises(ValueError, match="relative_lift"):
        required_sample_size(0.117, 0)
    with pytest.raises(ValueError, match="exceeds 1.0"):
        required_sample_size(0.9, 0.5)
