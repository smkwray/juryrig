"""Regression tests for the evaluation contract.

Guards against the two P0 bugs fixed in 2026-03-20:
1. Model selection must use validation split, not test.
2. Evaluation must filter to the best model before computing metrics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ny_oca_conviction.evaluation.report import evaluate_run


def _write_fixture(tmp_path: Path, predictions: pd.DataFrame, metrics: dict) -> str:
    """Write a minimal run directory and return the run_id."""
    run_id = "test_fixture"
    run_dir = tmp_path / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True)
    predictions.to_csv(run_dir / "predictions.csv", index=False)
    with (run_dir / "metrics.json").open("w") as f:
        json.dump(metrics, f)
    return run_id


def test_evaluate_run_filters_to_best_model(tmp_path, monkeypatch):
    """Subgroup/county/calibration outputs must come from the best model only."""
    # Two models with different predictions on the test split.
    rows = []
    for model, prob in [("model_a", 0.9), ("model_b", 0.1)]:
        for i in range(100):
            rows.append({
                "split": "test",
                "County": "TestCounty",
                "Race": "White",
                "Ethnicity": "Non-Hispanic",
                "Gender": "Male",
                "Region": "NYC",
                "age_bucket": "25-34",
                "y_true": 1 if i < 50 else 0,
                "model": model,
                "y_prob": prob,
            })

    predictions = pd.DataFrame(rows)
    metrics = {"best_model": "model_a", "models": {}}

    run_id = _write_fixture(tmp_path, predictions, metrics)

    # Monkeypatch to point at our fixture directory
    import ny_oca_conviction.evaluation.report as report_mod
    original_resolve = report_mod.resolve_run_directory
    report_mod.resolve_run_directory = lambda rid: tmp_path / "artifacts" / "runs" / rid

    # Also need to stub render_report since it needs the metrics structure
    original_render = report_mod.render_report
    report_mod.render_report = lambda *a, **kw: None

    try:
        result = evaluate_run(run_id, ["Race"])

        # Read the subgroup output — it should only have model_a predictions
        subgroup = pd.read_csv(result["subgroup_audit"])

        # model_a predicts 0.9 for everything, so brier on 50/50 data ≈ 0.5*0.9^2 + 0.5*0.1^2 = 0.41
        # model_b predicts 0.1, so brier ≈ 0.5*0.1^2 + 0.5*0.9^2 = 0.41 (same by symmetry)
        # But the key check: we should have 100 rows (one model), not 200 (both models)
        assert subgroup["row_count"].sum() == 100, (
            f"Expected 100 rows (single model), got {subgroup['row_count'].sum()} "
            "(evaluation is blending multiple models)"
        )
    finally:
        report_mod.resolve_run_directory = original_resolve
        report_mod.render_report = original_render


def test_evaluate_run_requires_best_model_key(tmp_path, monkeypatch):
    """evaluate_run must raise if metrics.json is missing best_model."""
    predictions = pd.DataFrame({
        "split": ["test"],
        "model": ["dummy"],
        "y_true": [1],
        "y_prob": [0.5],
    })
    metrics = {"models": {}}  # No best_model key

    run_id = _write_fixture(tmp_path, predictions, metrics)

    import ny_oca_conviction.evaluation.report as report_mod
    original_resolve = report_mod.resolve_run_directory
    report_mod.resolve_run_directory = lambda rid: tmp_path / "artifacts" / "runs" / rid

    try:
        with pytest.raises(ValueError, match="best_model"):
            evaluate_run(run_id, ["Race"])
    finally:
        report_mod.resolve_run_directory = original_resolve


def test_train_selects_on_validation_not_test():
    """Verify that metrics.json records validation as the selection split."""
    # This is a contract test — we check the code structure rather than
    # running the full pipeline (which requires data).
    import inspect

    from ny_oca_conviction.models.train import train_models

    source = inspect.getsource(train_models)

    # The selection filter must use "validation", not "test"
    assert 'split"] == "validation"' in source, (
        "Model selection must filter to validation split"
    )
    assert '"selection_split": "validation"' in source, (
        "metrics.json must record selection_split as validation"
    )
