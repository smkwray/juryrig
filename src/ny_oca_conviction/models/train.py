from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from sklearn.base import clone

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.features import resolve_feature_columns
from ny_oca_conviction.dataset.labels import LABEL_COLUMN
from ny_oca_conviction.evaluation.metrics import binary_metrics
from ny_oca_conviction.models.baselines import build_model_specs
from ny_oca_conviction.utils.io import read_json, write_json


def _load_train_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def train_models(config_path: Path) -> dict[str, str]:
    paths = ensure_project_layout()
    train_config = _load_train_config(config_path)
    dataset_summary = read_json(paths.processed / "model_table_summary.json")
    frame = pd.read_parquet(paths.processed / "model_table.parquet")
    feature_columns = dataset_summary.get("feature_columns") or resolve_feature_columns(frame)
    if not feature_columns:
        raise ValueError("No default feature columns are available for training.")

    frame = frame.copy()
    for column in feature_columns:
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().any():
            frame[column] = converted

    label_column = train_config.get("label_column", LABEL_COLUMN)
    random_state = int(train_config.get("random_state", 7))
    calibration = train_config.get("calibration", {})
    specs = build_model_specs(
        frame=frame,
        feature_columns=feature_columns,
        random_state=random_state,
        calibration_enabled=bool(calibration.get("enabled", True)),
        calibration_method=str(calibration.get("method", "sigmoid")),
    )

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = paths.runs / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    train_frame = frame[frame["split"] == "train"].copy()
    eval_frame = frame[frame["split"].isin(["validation", "test"])].copy()
    if train_frame.empty or eval_frame.empty:
        raise ValueError("Training requires non-empty train and validation/test splits.")

    X_train = train_frame[feature_columns]
    y_train = train_frame[label_column].astype(int)

    prediction_rows: list[pd.DataFrame] = []
    metrics_by_model: dict[str, dict[str, Any]] = {}
    best_model_name: str | None = None
    best_model_brier: float | None = None

    for spec in specs:
        estimator = clone(spec.estimator)
        if spec.name == "dummy":
            estimator.fit([[0]] * len(X_train), y_train)
            eval_probs = estimator.predict_proba([[0]] * len(eval_frame))[:, 1]
        else:
            estimator.fit(X_train, y_train)
            eval_probs = estimator.predict_proba(eval_frame[feature_columns])[:, 1]

        model_predictions = eval_frame[
            [
                "split",
                "County",
                "Race",
                "Ethnicity",
                "Gender",
                "Region",
                "age_bucket",
                label_column,
            ]
        ].copy()
        model_predictions.rename(columns={label_column: "y_true"}, inplace=True)
        model_predictions["model"] = spec.name
        model_predictions["y_prob"] = eval_probs
        prediction_rows.append(model_predictions)

        test_slice = model_predictions[model_predictions["split"] == "test"]
        metrics = binary_metrics(test_slice["y_true"], test_slice["y_prob"])
        metrics_by_model[spec.name] = metrics
        if best_model_brier is None or metrics["brier_score"] < best_model_brier:
            best_model_name = spec.name
            best_model_brier = metrics["brier_score"]

    predictions = pd.concat(prediction_rows, ignore_index=True)
    predictions.to_csv(run_dir / "predictions.csv", index=False)
    metrics_payload = {
        "run_id": run_id,
        "dataset_summary_path": str(paths.processed / "model_table_summary.json"),
        "config_path": str(config_path),
        "best_model": best_model_name,
        "models": metrics_by_model,
    }
    write_json(run_dir / "metrics.json", metrics_payload)
    return {"run_id": run_id, "run_dir": str(run_dir), "metrics": str(run_dir / "metrics.json")}
