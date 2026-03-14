from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from ny_oca_conviction.contracts.oca_stat_columns import (
    PROTECTED_ATTRIBUTES,
    default_training_columns,
)
from ny_oca_conviction.dataset.labels import LABEL_COLUMN, LABEL_STATUS_COLUMN
from ny_oca_conviction.dataset.maturity import (
    COHORT_COLUMN,
    DISPOSED_SHARE_COLUMN,
    MATURE_FLAG_COLUMN,
)

RESERVED_COLUMNS = {
    LABEL_COLUMN,
    LABEL_STATUS_COLUMN,
    COHORT_COLUMN,
    DISPOSED_SHARE_COLUMN,
    MATURE_FLAG_COLUMN,
    "split",
    "snapshot_date",
    "source_year",
    "source_filename",
    "age_bucket",
}


def resolve_feature_columns(
    frame: pd.DataFrame,
    drop_columns: Iterable[str] | None = None,
    protected_attribute_mode: str = "audit_only",
) -> list[str]:
    excluded = set(drop_columns or []) | RESERVED_COLUMNS
    include_protected_attributes = _include_protected_attributes(protected_attribute_mode)
    candidates = default_training_columns(
        frame.columns,
        include_protected_attributes=include_protected_attributes,
    )
    return [column for column in candidates if column not in excluded]


def audit_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column in PROTECTED_ATTRIBUTES]


def _include_protected_attributes(mode: str) -> bool:
    normalized = mode.strip().lower()
    if normalized == "audit_only":
        return False
    if normalized in {"include_all", "include_protected"}:
        return True
    raise ValueError(
        "protected_attribute_mode must be one of: audit_only, include_all, include_protected"
    )
