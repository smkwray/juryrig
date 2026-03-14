from __future__ import annotations

from pathlib import Path

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.evaluation.calibration import calibration_table
from ny_oca_conviction.evaluation.county_transfer import county_metrics
from ny_oca_conviction.evaluation.subgroup import subgroup_metrics
from ny_oca_conviction.reports.markdown import render_report
from ny_oca_conviction.utils.io import read_json


def resolve_run_directory(run_id: str) -> Path:
    runs_dir = ensure_project_layout().runs
    if run_id == "latest":
        candidates = sorted(path for path in runs_dir.iterdir() if path.is_dir())
        if not candidates:
            raise FileNotFoundError("No run directories exist under artifacts/runs.")
        return candidates[-1]
    return runs_dir / run_id


def evaluate_run(run_id: str, subgroup_columns: list[str]) -> dict[str, str]:
    run_dir = resolve_run_directory(run_id)
    predictions = pd.read_csv(run_dir / "predictions.csv")
    metrics_payload = read_json(run_dir / "metrics.json")

    test_predictions = predictions[predictions["split"] == "test"].copy()
    subgroup_frame = subgroup_metrics(test_predictions, subgroup_columns)
    county_frame = county_metrics(test_predictions)
    calibration_frame = calibration_table(test_predictions)

    subgroup_path = run_dir / "subgroup_audit.csv"
    county_path = run_dir / "county_transfer.csv"
    calibration_path = run_dir / "calibration_bins.csv"
    report_path = run_dir / "report.md"

    subgroup_frame.to_csv(subgroup_path, index=False)
    county_frame.to_csv(county_path, index=False)
    calibration_frame.to_csv(calibration_path, index=False)
    render_report(run_dir.name, metrics_payload, subgroup_frame, county_frame, report_path)

    return {
        "run_dir": str(run_dir),
        "subgroup_audit": str(subgroup_path),
        "county_transfer": str(county_path),
        "calibration_bins": str(calibration_path),
        "report": str(report_path),
    }
