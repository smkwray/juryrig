from __future__ import annotations

import math

import pandas as pd


def assign_time_splits(
    frame: pd.DataFrame,
    validation_fraction: float,
    test_fraction: float,
) -> pd.DataFrame:
    result = frame.copy()
    cohorts = (
        result[["Arraign Year", "Arraign Month"]]
        .drop_duplicates()
        .sort_values(["Arraign Year", "Arraign Month"])
        .reset_index(drop=True)
    )
    total = len(cohorts)
    if total == 0:
        result["split"] = pd.Series(dtype="string")
        return result

    test_count = 1 if total >= 2 else 0
    if total > 2:
        test_count = max(test_count, math.ceil(total * test_fraction))
    max_validation = max(total - test_count - 1, 0)
    validation_count = 0
    if total >= 3 and max_validation > 0:
        validation_count = min(max_validation, max(1, math.ceil(total * validation_fraction)))
    train_cutoff = total - validation_count - test_count

    cohorts["split"] = "train"
    if validation_count:
        cohorts.loc[train_cutoff : train_cutoff + validation_count - 1, "split"] = "validation"
    if test_count:
        cohorts.loc[total - test_count :, "split"] = "test"

    return result.merge(cohorts, on=["Arraign Year", "Arraign Month"], how="left")
