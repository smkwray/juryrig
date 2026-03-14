from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.features import audit_columns, resolve_feature_columns
from ny_oca_conviction.dataset.labels import LABEL_COLUMN, add_label_columns
from ny_oca_conviction.dataset.maturity import MATURE_FLAG_COLUMN, add_maturity_flags
from ny_oca_conviction.dataset.normalize import load_raw_oca_stat
from ny_oca_conviction.dataset.splits import assign_time_splits
from ny_oca_conviction.utils.io import write_json, write_markdown


def load_dataset_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _age_bucket(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    buckets = pd.cut(
        numeric,
        bins=[-1, 17, 24, 34, 44, 54, 64, 200],
        labels=["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
    )
    return buckets.astype("string").fillna("unknown")


def _string_key_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def build_dataset(
    snapshot_date: str | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    paths = ensure_project_layout()
    config = load_dataset_config(config_path or paths.configs / "dataset.yaml")
    frame = load_raw_oca_stat()
    frame = add_label_columns(frame)
    frame = add_maturity_flags(frame, float(config.get("maturity_threshold", 0.9)))
    frame = frame[frame[MATURE_FLAG_COLUMN] & frame[LABEL_COLUMN].notna()].copy()
    frame["snapshot_date"] = snapshot_date or date.today().isoformat()
    frame["age_bucket"] = _age_bucket(frame["Arrest Age"])
    split_config = config.get("split", {})
    frame = assign_time_splits(
        frame,
        validation_fraction=float(split_config.get("validation_fraction", 0.15)),
        test_fraction=float(split_config.get("test_fraction", 0.15)),
    )

    protected_attribute_mode = str(config.get("protected_attribute_mode", "audit_only"))
    feature_columns = resolve_feature_columns(
        frame,
        drop_columns=config.get("drop_columns", []),
        protected_attribute_mode=protected_attribute_mode,
    )
    audit_feature_columns = audit_columns(frame)

    output_path = paths.processed / "model_table.parquet"
    frame.to_parquet(output_path, index=False)

    summary = {
        "snapshot_date": frame["snapshot_date"].iloc[0] if not frame.empty else snapshot_date,
        "row_count": int(len(frame)),
        "feature_columns": feature_columns,
        "protected_attribute_mode": protected_attribute_mode,
        "audit_columns": audit_feature_columns,
        "split_counts": _string_key_counts(frame["split"]),
        "label_counts": _string_key_counts(frame[LABEL_COLUMN]),
        "county_counts": _string_key_counts(frame["County"]),
        "cohort_counts": {
            f"{year}-{month}": int(count)
            for (year, month), count in frame.groupby(["Arraign Year", "Arraign Month"])
            .size()
            .items()
        },
    }
    summary_path = paths.processed / "model_table_summary.json"
    write_json(summary_path, summary)
    write_markdown(
        paths.validation_artifacts / "dataset_summary.md",
        _render_dataset_summary(summary, output_path),
    )
    return {
        "model_table_path": str(output_path),
        "summary_path": str(summary_path),
        "row_count": summary["row_count"],
        "feature_count": len(feature_columns),
    }


def _render_dataset_summary(summary: dict[str, Any], output_path: Path) -> str:
    lines = [
        "# Dataset Summary",
        "",
        f"- output_path: {output_path}",
        f"- snapshot_date: {summary['snapshot_date']}",
        f"- row_count: {summary['row_count']}",
        f"- feature_count: {len(summary['feature_columns'])}",
        f"- protected_attribute_mode: {summary['protected_attribute_mode']}",
        "- audit_columns: "
        f"{', '.join(summary['audit_columns']) if summary['audit_columns'] else 'none'}",
        "",
        "## Split counts",
    ]
    for split_name, count in summary["split_counts"].items():
        lines.append(f"- {split_name}: {count}")
    lines.extend(["", "## Label counts"])
    for label, count in summary["label_counts"].items():
        lines.append(f"- {label}: {count}")
    return "\n".join(lines)
