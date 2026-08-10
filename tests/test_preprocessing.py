"""Preprocessing is where leakage gets in, so these are the tests that matter most."""

import numpy as np
import pytest

from term_deposit.preprocessing import (
    build_preprocessor,
    feature_columns,
    target_vector,
)
from term_deposit.splits import temporal_split


@pytest.fixture(scope="module")
def fitted(dated):
    train, test = temporal_split(dated)
    preprocessor = build_preprocessor()
    transformed = preprocessor.fit_transform(train[feature_columns()])
    return preprocessor, train, test, transformed


def test_duration_is_absent_by_default():
    assert "duration" not in feature_columns()


def test_duration_is_available_only_when_explicitly_requested():
    assert "duration" in feature_columns(include_duration=True)


def test_target_and_split_keys_never_reach_the_model():
    for column in ("y", "campaign_date", "campaign_year"):
        assert column not in feature_columns(include_duration=True)


def test_pdays_sentinel_becomes_an_explicit_indicator(fitted):
    preprocessor, *_ = fitted
    names = list(preprocessor.get_feature_names_out())
    assert "missingindicator_pdays" in names


def test_no_missing_values_survive_transformation(fitted):
    _, _, _, transformed = fitted
    assert not np.isnan(transformed).any()


def test_sentinel_rows_share_one_imputed_value(fitted):
    """Every "never contacted" row should look identical in the pdays column."""
    preprocessor, train, _, transformed = fitted
    names = list(preprocessor.get_feature_names_out())
    pdays_column = transformed[:, names.index("pdays")]
    never_contacted = (train["pdays"] == -1).to_numpy()
    assert len(np.unique(pdays_column[never_contacted])) == 1


def test_statistics_are_learned_from_training_data_only(fitted):
    """Transforming the test set must not change what the preprocessor knows."""
    preprocessor, _, test, _ = fitted
    before = preprocessor.named_transformers_["numeric"].mean_.copy()
    preprocessor.transform(test[feature_columns()])
    np.testing.assert_array_equal(before, preprocessor.named_transformers_["numeric"].mean_)


def test_unseen_categories_do_not_break_transformation(fitted):
    """The test period may contain job titles the training period never saw."""
    preprocessor, _, test, _ = fitted
    altered = test[feature_columns()].copy()
    altered.loc[altered.index[0], "job"] = "astronaut"
    assert not np.isnan(preprocessor.transform(altered)).any()


def test_an_all_sentinel_training_period_keeps_the_pdays_column(dated):
    """Nobody has a prior contact before 2008-10-21, so early windows are 100% sentinel.

    A median imputer has nothing to learn from there and drops the feature, quietly
    changing the feature set depending on which period the model is trained on.
    """
    earliest = dated.head(3000)
    assert (earliest["pdays"] == -1).all()

    preprocessor = build_preprocessor()
    preprocessor.fit(earliest[feature_columns()])
    names = list(preprocessor.get_feature_names_out())
    assert "pdays" in names
    assert "missingindicator_pdays" in names


def test_target_encodes_subscriptions_as_one(dated):
    encoded = target_vector(dated)
    assert set(encoded.unique()) == {0, 1}
    assert encoded.sum() == dated.y.eq("yes").sum()
