from __future__ import annotations

from dataclasses import dataclass

POSITIVE_DISPOSITIONS = {"Plea", "Verdict-TFG"}
NEGATIVE_DISPOSITIONS = {"Dismissed", "Dism-ACD", "Verdict-ACQ"}
EXCLUDED_DISPOSITIONS = {
    "Pending",
    "Tolled/Open Warrant",
    "Open Warrant",
    "GJ/Trans",
    "Other",
    "Unknown",
}
DISPOSED_STATUSES = {"Disposed"}


@dataclass(frozen=True)
class LabelPolicy:
    maturity_threshold: float = 0.9


def map_disposition_to_label(disposition_type: str | None) -> int | None:
    value = (disposition_type or "").strip()
    if value in POSITIVE_DISPOSITIONS:
        return 1
    if value in NEGATIVE_DISPOSITIONS:
        return 0
    return None


def is_excluded_disposition(disposition_type: str | None) -> bool:
    return (disposition_type or "").strip() in EXCLUDED_DISPOSITIONS


def is_disposed_status(docket_status: str | None) -> bool:
    return (docket_status or "").strip() in DISPOSED_STATUSES
