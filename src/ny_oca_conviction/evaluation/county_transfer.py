from __future__ import annotations

import pandas as pd

from ny_oca_conviction.evaluation.metrics import binary_metrics


def county_metrics(frame: pd.DataFrame, min_rows: int = 50) -> pd.DataFrame:
    if "County" not in frame.columns:
        return pd.DataFrame(columns=["County"])
    rows: list[dict[str, object]] = []
    for county, group in frame.groupby("County", dropna=False):
        if len(group) < min_rows:
            continue
        rows.append({"County": county, **binary_metrics(group["y_true"], group["y_prob"])})
    return pd.DataFrame(rows)
