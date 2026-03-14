from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MaxAbsScaler, OneHotEncoder, OrdinalEncoder

from ny_oca_conviction.models.calibrate import maybe_calibrate


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: object


def _split_feature_types(
    frame: pd.DataFrame,
    feature_columns: list[str],
) -> tuple[list[str], list[str]]:
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    for column in feature_columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series):
            numeric_columns.append(column)
            continue
        coerced = pd.to_numeric(series, errors="coerce")
        if coerced.notna().any():
            numeric_columns.append(column)
        else:
            categorical_columns.append(column)
    return numeric_columns, categorical_columns


def _numeric_transformer() -> Pipeline:
    return Pipeline([("imputer", SimpleImputer(strategy="median"))])


def _categorical_one_hot() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )


def _categorical_ordinal() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encode", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
        ]
    )


def _scaled_logistic_regression(random_state: int) -> Pipeline:
    # Keep the linear baseline sparse-friendly: one-hot encode, scale magnitudes, then fit saga.
    return Pipeline(
        [
            ("scale", MaxAbsScaler()),
            (
                "model",
                LogisticRegression(
                    solver="saga",
                    max_iter=2000,
                    tol=1e-3,
                    random_state=random_state,
                ),
            ),
        ]
    )


def build_model_specs(
    frame: pd.DataFrame,
    feature_columns: list[str],
    random_state: int,
    calibration_enabled: bool,
    calibration_method: str,
) -> list[ModelSpec]:
    numeric_columns, categorical_columns = _split_feature_types(frame, feature_columns)
    linear_preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", _numeric_transformer(), numeric_columns),
            ("categorical", _categorical_one_hot(), categorical_columns),
        ]
    )
    tree_preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", _numeric_transformer(), numeric_columns),
            ("categorical", _categorical_ordinal(), categorical_columns),
        ],
        sparse_threshold=0.0,
    )

    return [
        ModelSpec(
            name="dummy",
            estimator=DummyClassifier(strategy="prior", random_state=random_state),
        ),
        ModelSpec(
            name="logistic_regression",
            estimator=Pipeline(
                [
                    ("preprocess", linear_preprocessor),
                    ("linear", _scaled_logistic_regression(random_state)),
                ]
            ),
        ),
        ModelSpec(
            name="hist_gradient_boosting",
            estimator=Pipeline(
                [
                    ("preprocess", tree_preprocessor),
                    (
                        "model",
                        maybe_calibrate(
                            HistGradientBoostingClassifier(random_state=random_state),
                            enabled=calibration_enabled,
                            method=calibration_method,
                        ),
                    ),
                ]
            ),
        ),
    ]
