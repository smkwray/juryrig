from __future__ import annotations

import re
from collections.abc import Iterable

CANONICAL_COLUMNS = [
    "Row #",
    "Court Type",
    "Region",
    "District",
    "County",
    "Court",
    "Arresting Agency",
    "Arrest Type",
    "Arraign Year",
    "Arraign Month",
    "Top Charge at Arraignment",
    "Severity",
    "Weight",
    "Law",
    "Article.Section",
    "Attempt Flag",
    "Gender",
    "Ethnicity",
    "Race",
    "Arrest Age",
    "Docket Status",
    "Disposition Type",
    "Disposition Detail",
    "Dismissal Reason",
    "Most Severe Sentence",
    "Fines Imposed",
    "Fees Imposed",
    "Surcharges Imposed",
]

LEAKAGE_DENYLIST = {
    "Docket Status",
    "Disposition Type",
    "Disposition Detail",
    "Dismissal Reason",
    "Most Severe Sentence",
    "Fines Imposed",
    "Fees Imposed",
    "Surcharges Imposed",
}

PROTECTED_ATTRIBUTES = {"Gender", "Ethnicity", "Race"}
IDENTIFIER_COLUMNS = {"Row #"}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


_ALIASES = {_slug(name): name for name in CANONICAL_COLUMNS}
_ALIASES.update(
    {
        "row": "Row #",
        "arraignyear": "Arraign Year",
        "arraignmonth": "Arraign Month",
        "articlesection": "Article.Section",
        "topchargeatarraignment": "Top Charge at Arraignment",
    }
)


def normalize_column_name(name: str) -> str:
    return _ALIASES.get(_slug(name.strip()), name.strip())


def normalize_columns(columns: Iterable[str]) -> list[str]:
    return [normalize_column_name(column) for column in columns]


def missing_columns(columns: Iterable[str]) -> list[str]:
    normalized = set(normalize_columns(columns))
    return [column for column in CANONICAL_COLUMNS if column not in normalized]


def unexpected_columns(columns: Iterable[str]) -> list[str]:
    normalized = set(normalize_columns(columns))
    return sorted(column for column in normalized if column not in CANONICAL_COLUMNS)


def default_training_columns(
    columns: Iterable[str],
    include_protected_attributes: bool = False,
) -> list[str]:
    selected: list[str] = []
    for column in normalize_columns(columns):
        if (
            column in LEAKAGE_DENYLIST
            or (column in PROTECTED_ATTRIBUTES and not include_protected_attributes)
            or column in IDENTIFIER_COLUMNS
        ):
            continue
        selected.append(column)
    return selected
