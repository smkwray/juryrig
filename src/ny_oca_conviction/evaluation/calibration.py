from __future__ import annotations

import pandas as pd


def calibration_table(frame: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["bin", "count", "avg_prediction", "avg_outcome"])
    working = frame.copy()
    working["bin"] = pd.qcut(working["y_prob"], q=min(bins, len(working)), duplicates="drop")
    grouped = (
        working.groupby("bin", observed=False)
        .agg(
            count=("y_prob", "size"),
            avg_prediction=("y_prob", "mean"),
            avg_outcome=("y_true", "mean"),
        )
        .reset_index()
    )
    grouped["bin"] = grouped["bin"].astype("string")
    return grouped
