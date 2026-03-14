from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.contracts.oca_stat_columns import (
    CANONICAL_COLUMNS,
    missing_columns,
    normalize_columns,
    unexpected_columns,
)
from ny_oca_conviction.data_access.manifest import load_manifest
from ny_oca_conviction.utils.io import write_markdown


@dataclass(frozen=True)
class RawValidationResult:
    year: int
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


def validate_raw_files() -> tuple[list[RawValidationResult], Path]:
    paths = ensure_project_layout()
    manifest = load_manifest()
    results: list[RawValidationResult] = []
    for entry in manifest.files:
        csv_path = paths.raw_oca_stat / entry.filename
        if not csv_path.exists():
            results.append(
                RawValidationResult(
                    year=entry.year,
                    filename=entry.filename,
                    exists=False,
                    column_count=0,
                    missing=CANONICAL_COLUMNS.copy(),
                    unexpected=[],
                    duplicate_columns=[],
                )
            )
            continue
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        normalized = normalize_columns(header)
        duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
        results.append(
            RawValidationResult(
                year=entry.year,
                filename=entry.filename,
                exists=True,
                column_count=len(header),
                missing=missing_columns(header),
                unexpected=unexpected_columns(header),
                duplicate_columns=duplicates,
            )
        )
    report_path = paths.validation_artifacts / "raw_schema_report.md"
    write_markdown(report_path, _render_report(results))
    return results, report_path


def _render_report(results: list[RawValidationResult]) -> str:
    lines = ["# Raw Schema Validation", ""]
    if not results:
        lines.extend(["No manifest entries found.", ""])
        return "\n".join(lines)
    for result in results:
        lines.append(f"## {result.year} - {result.filename}")
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
