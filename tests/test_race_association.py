import math

import pandas as pd

from ny_oca_conviction.evaluation.race_association import (
    _compute_matched_strata_differences,
    _race_categories,
)


def test_race_categories_places_white_first():
    series = pd.Series(["Black", "White", "Asian", "Unknown"])
    assert _race_categories(series) == ["White", "Asian", "Black", "Unknown"]


def test_matched_strata_differences_returns_weighted_gap():
    frame = pd.DataFrame(
        {
            "County": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "Court Type": ["Local"] * 8,
            "Arrest Type": ["DAT"] * 8,
            "Severity": ["Misdemeanor"] * 8,
            "Weight": ["A"] * 8,
            "age_bucket": ["25-34"] * 8,
            "Ethnicity": ["Non-Hispanic"] * 8,
            "Gender": ["Male"] * 8,
            "Arraign Year": ["2021"] * 8,
            "Arraign Month": ["1"] * 8,
            "Race": [
                "White",
                "White",
                "Black",
                "Black",
                "White",
                "White",
                "Black",
                "Black",
            ],
            "conviction_label": [1, 0, 0, 0, 1, 1, 1, 0],
        }
    )

    result = _compute_matched_strata_differences(
        frame=frame,
        race_values=["White", "Black"],
        strata_columns=[
            "County",
            "Court Type",
            "Arrest Type",
            "Severity",
            "Weight",
            "age_bucket",
            "Ethnicity",
            "Gender",
            "Arraign Year",
            "Arraign Month",
        ],
        reference_race="White",
    )

    row = result.iloc[0]
    assert row["race"] == "Black"
    assert row["shared_strata_count"] == 2
    assert row["shared_reference_rows"] == 4
    assert row["shared_comparison_rows"] == 4
    assert math.isclose(row["weighted_diff_vs_white_pp"], -50.0, abs_tol=1e-9)
    assert math.isclose(row["shared_reference_share"], 1.0, abs_tol=1e-9)
    assert math.isclose(row["shared_comparison_share"], 1.0, abs_tol=1e-9)
