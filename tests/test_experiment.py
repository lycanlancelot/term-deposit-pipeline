"""Smoke tests for the grid — correctness of the parts is covered elsewhere."""

import pytest

from term_deposit.experiment import (
    REFERENCE_MODEL,
    SPLIT_STRATEGIES,
    reference_comparison,
    run_grid,
    segment_evaluation,
)
from term_deposit.models import build_models


@pytest.fixture(scope="module")
def grid(dated):
    """A slice spanning both sides of the first prior-contact date, to keep it quick."""
    return run_grid(dated.iloc[:6000])


def test_every_combination_is_evaluated(grid):
    assert len(grid) == len(SPLIT_STRATEGIES) * 3 * 2  # splits x models x feature sets
    assert set(grid.split) == set(SPLIT_STRATEGIES)


def test_train_and_test_never_overlap_in_size(grid, dated):
    assert (grid.n_train + grid.n_test == 6000).all()


def test_leakage_shows_up_as_a_better_score(grid):
    """A sanity check on the whole apparatus: duration should help, a lot."""
    boosted = grid[grid.model == "gradient_boosting"].set_index(["split", "features"])
    for split in SPLIT_STRATEGIES:
        assert (
            boosted.loc[(split, "with duration"), "roc_auc"]
            > boosted.loc[(split, "no duration"), "roc_auc"]
        ), split


def test_the_reference_model_actually_exists():
    assert REFERENCE_MODEL in build_models()


def test_reference_comparison_reports_paired_uncertainty(dated):
    comparison = reference_comparison(dated.iloc[:6000])
    assert set(comparison.metric) == {"roc_auc", "pr_auc"}
    for _, row in comparison.iterrows():
        for interval in (row.logistic_regression_ci, row.gradient_boosting_ci, row.delta_ci):
            assert interval[0] <= interval[1]


def test_segment_evaluation_partitions_the_test_set(dated):
    """Full frame: the reference model is cheap to fit, and the slice fixtures predate
    the first re-contact (2008-10-21), which would leave that segment empty."""
    segments = segment_evaluation(dated).set_index("segment")
    assert (
        segments.loc["cold call (pdays == -1)", "n"] + segments.loc["re-contact (pdays >= 0)", "n"]
        == segments.loc["all", "n"]
    )


def test_segment_evaluation_skips_segments_it_cannot_score(dated):
    """On an early slice nobody has been contacted before, so only viable rows appear."""
    early = segment_evaluation(dated.iloc[:6000])
    assert "re-contact (pdays >= 0)" not in set(early.segment)
    assert len(early) >= 1


def test_the_prior_baseline_ranks_no_better_than_chance(grid):
    """A constant score carries no ordering, so it must land exactly on 0.5."""
    prior = grid[grid.model == "prior"]
    assert prior.roc_auc.sub(0.5).abs().max() < 1e-9
