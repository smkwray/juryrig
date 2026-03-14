import pandas as pd

from ny_oca_conviction.dataset.splits import assign_time_splits


def test_split_assignment_reserves_latest_cohorts_for_validation_and_test():
    frame = pd.DataFrame(
        {
            "Arraign Year": [2024, 2024, 2024, 2024, 2025, 2025],
            "Arraign Month": [1, 2, 3, 4, 1, 2],
        }
    )
    assigned = assign_time_splits(frame, validation_fraction=0.2, test_fraction=0.2)
    latest = assigned.sort_values(["Arraign Year", "Arraign Month"]).drop_duplicates(
        ["Arraign Year", "Arraign Month"]
    )
    assert latest.iloc[-1]["split"] == "test"
    assert "validation" in set(latest["split"])
