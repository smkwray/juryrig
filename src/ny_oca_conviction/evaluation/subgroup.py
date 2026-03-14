from __future__ import annotations

import pandas as pd

from ny_oca_conviction.evaluation.metrics import binary_metrics


def subgroup_metrics(frame: pd.DataFrame, columns: list[str], min_rows: int = 20) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in columns:
        if column not in frame.columns:
            continue
        for value, group in frame.groupby(column, dropna=False):
            if len(group) < min_rows:
                continue
            metrics = binary_metrics(group["y_true"], group["y_prob"])
            rows.append({"column": column, "value": value, **metrics})
    return pd.DataFrame(rows)
