from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.normalize_supplemental_pretrial import load_raw_supplemental_pretrial
from ny_oca_conviction.utils.io import write_json, write_markdown


def _value_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def summarize_supplemental_pretrial() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = load_raw_supplemental_pretrial()
    summary = {
        "row_count": int(len(frame)),
        "column_count": int(len([column for column in frame.columns if column != "source_file"])),
        "source_file_counts": _value_counts(frame["source_file"]),
        "year_counts": _value_counts(frame["larg_yr"]),
        "arraignment_region_counts": _value_counts(frame["larg_county_name"]),
        "release_decision_counts": _value_counts(frame["larg_rel_decision"]),
        "disposition_counts": _value_counts(frame["disposition"]),
    }
    summary_path = paths.processed_supplemental_pretrial / "summary.json"
    write_json(summary_path, summary)
    report_path = paths.validation_artifacts / "supplemental_pretrial_summary.md"
    write_markdown(report_path, _render_summary(summary, summary_path))
    return {
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "row_count": summary["row_count"],
        "column_count": summary["column_count"],
    }


def _render_summary(summary: dict[str, Any], summary_path: Path) -> str:
    lines = [
        "# Supplemental Pretrial Summary",
        "",
        f"- summary_path: {summary_path}",
        f"- row_count: {summary['row_count']}",
        f"- column_count: {summary['column_count']}",
        "",
        "## Source file counts",
    ]
    for key, value in summary["source_file_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Arraignment year counts",
    ])
    for key, value in summary["year_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Largest arraignment release decisions"])
    for key, value in summary["release_decision_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Final dispositions"])
    for key, value in summary["disposition_counts"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
