from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ny_oca_conviction.reports.templates import report_header


def _frame_as_markdown_list(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return []
    header = "| " + " | ".join(frame.columns.astype(str)) + " |"
    separator = "|" + "|".join([" --- "] * len(frame.columns)) + "|"
    rows = [header, separator]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(value) for value in row.tolist()) + " |")
    return rows


def render_report(
    run_id: str,
    metrics: dict[str, Any],
    subgroup_frame: pd.DataFrame,
    county_frame: pd.DataFrame,
    output_path: Path,
) -> Path:
    best_model = metrics.get("best_model")
    lines = [report_header(run_id, best_model)]
    lines.append("## Model metrics")
    for model_name, model_metrics in metrics.get("models", {}).items():
        lines.append(f"### {model_name}")
        for key, value in model_metrics.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.append("## Subgroup audit")
    if subgroup_frame.empty:
        lines.append("No subgroup metrics available.")
    else:
        lines.extend(_frame_as_markdown_list(subgroup_frame))
    lines.append("")
    lines.append("## County transfer")
    if county_frame.empty:
        lines.append("No county transfer metrics available.")
    else:
        lines.extend(_frame_as_markdown_list(county_frame))
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output_path
