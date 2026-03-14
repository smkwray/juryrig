from __future__ import annotations

import pandas as pd

from ny_oca_conviction.contracts.label_contract import (
    EXCLUDED_DISPOSITIONS,
    map_disposition_to_label,
)

LABEL_COLUMN = "conviction_label"
LABEL_STATUS_COLUMN = "label_status"


def add_label_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    disposition = result["Disposition Type"].astype("string")
    result[LABEL_COLUMN] = disposition.map(map_disposition_to_label).astype("Int64")
    result[LABEL_STATUS_COLUMN] = "unlabeled"
    result.loc[result[LABEL_COLUMN].notna(), LABEL_STATUS_COLUMN] = "modeled"
    result.loc[disposition.isin(EXCLUDED_DISPOSITIONS), LABEL_STATUS_COLUMN] = "excluded"
    return result
