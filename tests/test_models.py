import pandas as pd
from sklearn.pipeline import Pipeline

from ny_oca_conviction.models.baselines import _scaled_logistic_regression, _split_feature_types


def test_scaled_logistic_regression_uses_sparse_friendly_solver():
    pipeline = _scaled_logistic_regression(random_state=7)
    assert isinstance(pipeline, Pipeline)
    assert pipeline.named_steps["model"].solver == "saga"
    assert pipeline.named_steps["model"].max_iter == 2000


def test_split_feature_types_forces_categorical_for_numeric_looking_codes():
    frame = pd.DataFrame({
        "Article.Section": ["120.00", "265.03", "155.25"],
        "Law": ["PL", "PL", "VTL"],
        "Arrest Age": [25, 30, 45],
    })
    numeric, categorical = _split_feature_types(frame, ["Article.Section", "Law", "Arrest Age"])
    assert "Article.Section" in categorical
    assert "Law" in categorical
    assert "Arrest Age" in numeric
