from sklearn.pipeline import Pipeline

from ny_oca_conviction.models.baselines import _scaled_logistic_regression


def test_scaled_logistic_regression_uses_sparse_friendly_solver():
    pipeline = _scaled_logistic_regression(random_state=7)
    assert isinstance(pipeline, Pipeline)
    assert pipeline.named_steps["model"].solver == "saga"
    assert pipeline.named_steps["model"].max_iter == 2000
