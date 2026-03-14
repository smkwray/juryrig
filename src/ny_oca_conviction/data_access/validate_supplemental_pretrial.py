from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.contracts.supplemental_pretrial_columns import (
    CANONICAL_COLUMNS,
    missing_columns,
    normalize_columns,
    unexpected_columns,
)
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import load_manifest
from ny_oca_conviction.utils.io import write_markdown


@dataclass(frozen=True)
class SupplementalValidationResult:
    role: str
    filename: str
    exists: bool
    column_count: int
    missing: list[str]
    unexpected: list[str]
    duplicate_columns: list[str]

    @property
    def ok(self) -> bool:
        return (
            self.exists and not self.missing and not self.unexpected and not self.duplicate_columns
        )


def validate_supplemental_pretrial_files() -> tuple[list[SupplementalValidationResult], Path]:
    paths = ensure_project_layout()
    manifest = load_manifest()
    data_csvs = manifest.find_by_prefix("data_csv_part_")
    if not data_csvs:
        result = SupplementalValidationResult(
            role="data_csv",
            filename="",
            exists=False,
            column_count=0,
            missing=CANONICAL_COLUMNS.copy(),
            unexpected=[],
            duplicate_columns=[],
        )
        report_path = paths.validation_artifacts / "supplemental_pretrial_schema_report.md"
        write_markdown(report_path, _render_report([result]))
        return [result], report_path

    results = [
        _validate_csv(paths.raw_supplemental_pretrial / data_csv.filename, data_csv.role)
        for data_csv in data_csvs
    ]
    report_path = paths.validation_artifacts / "supplemental_pretrial_schema_report.md"
    write_markdown(report_path, _render_report(results))
    return results, report_path


def _validate_csv(csv_path: Path, role: str = "data_csv") -> SupplementalValidationResult:
    if not csv_path.exists():
        return SupplementalValidationResult(
            role=role,
            filename=csv_path.name,
            exists=False,
            column_count=0,
            missing=CANONICAL_COLUMNS.copy(),
            unexpected=[],
            duplicate_columns=[],
        )

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
    normalized = normalize_columns(header)
    duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
    return SupplementalValidationResult(
        role=role,
        filename=csv_path.name,
        exists=True,
        column_count=len(header),
        missing=missing_columns(header),
        unexpected=unexpected_columns(header),
        duplicate_columns=duplicates,
    )


def _render_report(results: list[SupplementalValidationResult]) -> str:
    lines = ["# Supplemental Pretrial Schema Validation", ""]
    for result in results:
        lines.append(f"## {result.role}")
        lines.append(f"- filename: {result.filename or 'none'}")
        lines.append(f"- exists: {result.exists}")
        lines.append(f"- column_count: {result.column_count}")
        lines.append(f"- missing: {', '.join(result.missing) if result.missing else 'none'}")
        lines.append(
            f"- unexpected: {', '.join(result.unexpected) if result.unexpected else 'none'}"
        )
        lines.append(
            "- duplicate_columns: "
            f"{', '.join(result.duplicate_columns) if result.duplicate_columns else 'none'}"
        )
        lines.append(f"- status: {'ok' if result.ok else 'fail'}")
        lines.append("")
    return "\n".join(lines)
