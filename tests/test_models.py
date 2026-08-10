import numpy as np
import pytest

from term_deposit.models import build_models
from term_deposit.preprocessing import feature_columns, target_vector


@pytest.fixture(scope="module")
def sample(dated):
    """A small slice — these tests check plumbing, not performance."""
    return dated.head(3000)


def test_every_model_shares_the_same_raw_frame_interface(sample):
    """Preprocessing lives inside each pipeline, so all three take the raw columns."""
    features, target = sample[feature_columns()], target_vector(sample)
    for name, model in build_models().items():
        probabilities = model.fit(features, target).predict_proba(features)[:, 1]
        assert probabilities.shape == (len(sample),), name
        assert ((probabilities >= 0) & (probabilities <= 1)).all(), name


def test_prior_baseline_predicts_the_training_base_rate_for_everyone(sample):
    features, target = sample[feature_columns()], target_vector(sample)
    model = build_models()["prior"].fit(features, target)
    predictions = model.predict_proba(features)[:, 1]
    assert np.allclose(predictions, target.mean())


def test_real_models_actually_discriminate(sample):
    features, target = sample[feature_columns()], target_vector(sample)
    for name in ("logistic_regression", "gradient_boosting"):
        predictions = build_models()[name].fit(features, target).predict_proba(features)[:, 1]
        assert predictions.std() > 0.01, name


def test_the_same_seed_reproduces_the_same_predictions(sample):
    features, target = sample[feature_columns()], target_vector(sample)
    first = build_models(seed=7)["gradient_boosting"].fit(features, target).predict_proba(features)
    second = build_models(seed=7)["gradient_boosting"].fit(features, target).predict_proba(features)
    np.testing.assert_array_equal(first, second)


def test_duration_reaches_the_model_only_when_requested(sample):
    """The leakage flag has to survive all the way through the pipeline."""
    with_leak = build_models(include_duration=True)["logistic_regression"]
    fitted = with_leak.fit(sample[feature_columns(include_duration=True)], target_vector(sample))
    assert "duration" in fitted.named_steps["features"].get_feature_names_out()

    without = build_models()["logistic_regression"]
    fitted = without.fit(sample[feature_columns()], target_vector(sample))
    assert "duration" not in fitted.named_steps["features"].get_feature_names_out()
