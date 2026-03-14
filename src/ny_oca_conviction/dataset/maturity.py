from __future__ import annotations

import pandas as pd

from ny_oca_conviction.contracts.label_contract import is_disposed_status

MATURE_FLAG_COLUMN = "is_mature_cohort"
DISPOSED_SHARE_COLUMN = "disposed_share"
COHORT_COLUMN = "arraign_cohort"


def add_maturity_flags(frame: pd.DataFrame, threshold: float) -> pd.DataFrame:
    result = frame.copy()
    year = pd.to_numeric(result["Arraign Year"], errors="coerce").astype("Int64")
    month = pd.to_numeric(result["Arraign Month"], errors="coerce").astype("Int64")
    result["Arraign Year"] = year
    result["Arraign Month"] = month
    result[COHORT_COLUMN] = year.astype("string") + "-" + month.astype("string").str.zfill(2)
    result["_is_disposed"] = result["Docket Status"].map(is_disposed_status).fillna(False)
    cohort_summary = (
        result.groupby(["Arraign Year", "Arraign Month"], dropna=False)["_is_disposed"]
        .mean()
        .reset_index()
        .rename(columns={"_is_disposed": DISPOSED_SHARE_COLUMN})
    )
    result = result.merge(cohort_summary, on=["Arraign Year", "Arraign Month"], how="left")
    result[MATURE_FLAG_COLUMN] = result[DISPOSED_SHARE_COLUMN].fillna(0.0) >= threshold
    return result.drop(columns=["_is_disposed"])
