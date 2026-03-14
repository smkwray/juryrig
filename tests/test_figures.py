import pandas as pd

from ny_oca_conviction.reports.figures import (
    _exposure_label,
    _render_predictive_metrics_svg,
    _render_pretrial_release_diffs_svg,
    _render_pretrial_release_trend_svg,
    _render_race_adjusted_gap_svg,
    _render_race_positive_rate_svg,
    _scale_value,
)


def test_scale_value_maps_range_endpoints():
    assert _scale_value(-1.0, -1.0, 1.0, 10.0, 110.0) == 10.0
    assert _scale_value(1.0, -1.0, 1.0, 10.0, 110.0) == 110.0


def test_exposure_label_maps_known_groups():
    row = pd.Series({"exposure_group": "2022_new_qualifying_firearm_charge"})
    assert _exposure_label(row) == "2022 new firearm"


def test_svg_renderers_emit_expected_labels():
    metrics = {
        "models": {
            "dummy": {"auroc": 0.5, "pr_auc": 0.4, "brier_score": 0.25},
            "logistic_regression": {"auroc": 0.84, "pr_auc": 0.81, "brier_score": 0.16},
            "hist_gradient_boosting": {"auroc": 0.86, "pr_auc": 0.83, "brier_score": 0.15},
        }
    }
    svg = _render_predictive_metrics_svg(metrics)
    assert "Predictive branch: model comparison" in svg
    assert "Hist GB" in svg

    diffs = pd.DataFrame(
        {
            "court_type": ["NYC Criminal Courts"],
            "exposure_group": ["2022_new_qualifying_firearm_charge"],
            "diff_vs_comparison_released_share_known": [-0.2],
        }
    )
    policy_summary = {"row_count": 853976}
    svg = _render_pretrial_release_diffs_svg(diffs, policy_summary)
    assert "release-rate change vs comparison group" in svg
    assert "2022 new firearm" in svg

    subgroup = pd.DataFrame(
        {
            "column": ["Race", "Race"],
            "value": ["Asian", "White"],
            "row_count": [10, 20],
            "positive_rate": [0.2, 0.4],
            "brier_score": [0.18, 0.17],
            "auroc": [0.68, 0.76],
        }
    )
    svg = _render_race_positive_rate_svg(subgroup)
    assert "Observed conviction rate by race" in svg
    assert "Overall 33.3%" in svg

    race_association = {
        "reference_race": "White",
        "adjusted_models": {
            "core_adjusted": {
                "standardized_probability_table": [
                    {"race": "White", "diff_vs_white_pp": 0.0},
                    {"race": "Black", "diff_vs_white_pp": -2.7},
                    {"race": "Asian", "diff_vs_white_pp": -5.3},
                ]
            },
            "charge_detail_adjusted": {
                "standardized_probability_table": [
                    {"race": "White", "diff_vs_white_pp": 0.0},
                    {"race": "Black", "diff_vs_white_pp": -2.8},
                    {"race": "Asian", "diff_vs_white_pp": -5.2},
                ]
            },
        },
        "matched_strata": {
            "comparisons": [
                {"race": "Black", "weighted_diff_vs_white_pp": -2.6},
                {"race": "Asian", "weighted_diff_vs_white_pp": -6.7},
            ]
        },
    }
    svg = _render_race_adjusted_gap_svg(race_association)
    assert "Adjusted race gaps vs White defendants" in svg
    assert "Matched strata" in svg

    monthly_release = pd.DataFrame(
        {
            "year_month": [
                "2021-01",
                "2022-05",
                "2023-06",
                "2021-01",
                "2022-05",
                "2023-06",
            ],
            "court_type": [
                "NYC Criminal Courts",
                "NYC Criminal Courts",
                "NYC Criminal Courts",
                "Non-NYC City and District Courts",
                "Non-NYC City and District Courts",
                "Non-NYC City and District Courts",
            ],
            "released_count": [80, 82, 81, 70, 69, 68],
            "release_decision_known": [100, 100, 100, 100, 100, 100],
        }
    )
    svg = _render_pretrial_release_trend_svg(monthly_release, policy_summary)
    assert "Monthly pretrial release rates" in svg
    assert "May 2022" in svg
