from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.normalize_supplemental_pretrial import load_raw_supplemental_pretrial
from ny_oca_conviction.dataset.replicate_supplemental_pretrial import COURT_TYPE_MAP
from ny_oca_conviction.utils.io import write_json, write_markdown

POLICY_START = (2021, 1)
POLICY_END = (2024, 12)
AMENDMENT_2022 = (2022, 5)
AMENDMENT_2023 = (2023, 6)
HARM_OR_PROPERTY_ARTICLES = {
    "120",
    "121",
    "125",
    "130",
    "135",
    "140",
    "145",
    "150",
    "155",
    "160",
    "165",
}


def build_supplemental_pretrial_policy_sample() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = load_raw_supplemental_pretrial()
    sample = _policy_sample(frame)
    output_dir = paths.processed_supplemental_pretrial

    sample_path = output_dir / "policy_sample.parquet"
    crosswalk_path = output_dir / "charge_exposure_template.csv"
    summary_path = output_dir / "policy_sample_summary.json"
    report_path = paths.validation_artifacts / "supplemental_pretrial_policy_sample.md"

    sample.to_parquet(sample_path, index=False)
    crosswalk = _charge_exposure_template(sample)
    crosswalk.to_csv(crosswalk_path, index=False)

    summary = {
        "row_count": int(len(sample)),
        "column_count": int(len(sample.columns)),
        "court_type_counts": _value_counts(sample["court_type"]),
        "year_counts": _value_counts(sample["arraign_year"]),
        "month_counts": _value_counts(sample["arraign_month"]),
        "release_decision_counts": _value_counts(sample["larg_rel_decision"]),
        "disposition_counts": _value_counts(sample["disposition"]),
        "post_2022_count": int(sample["post_2022_amendment"].sum()),
        "post_2023_count": int(sample["post_2023_amendment"].sum()),
        "crosswalk_charge_rows": int(len(crosswalk)),
        "row_exposure_2022_counts": _value_counts(sample["row_exposure_2022"]),
        "row_exposure_2023_counts": _value_counts(sample["row_exposure_2023"]),
    }
    write_json(summary_path, summary)
    write_markdown(
        report_path,
        _render_policy_sample_report(summary, sample_path, crosswalk_path, summary_path),
    )
    return {
        "policy_sample_path": str(sample_path),
        "charge_exposure_template_path": str(crosswalk_path),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "row_count": summary["row_count"],
        "crosswalk_charge_rows": summary["crosswalk_charge_rows"],
    }


def load_supplemental_pretrial_policy_sample() -> pd.DataFrame:
    paths = ensure_project_layout()
    sample_path = paths.processed_supplemental_pretrial / "policy_sample.parquet"
    if sample_path.exists():
        return pd.read_parquet(sample_path)
    return _policy_sample(load_raw_supplemental_pretrial())


def _policy_sample(frame: pd.DataFrame) -> pd.DataFrame:
    sample = frame[frame["larg_court_type"].isin(COURT_TYPE_MAP)].copy()
    sample["court_type"] = sample["larg_court_type"].map(COURT_TYPE_MAP)
    sample["arraign_year"] = pd.to_numeric(sample["larg_yr"], errors="coerce").astype("Int64")
    sample["arraign_month"] = pd.to_numeric(sample["larg_mo"], errors="coerce").astype("Int64")
    sample = sample[sample["court_type"] != "Non-NYC Town and Village Justice Courts"].copy()
    sample = sample[sample["arraign_year"].between(POLICY_START[0], POLICY_END[0])].copy()
    sample = sample[sample["arraign_month"].between(1, 12)].copy()
    sample["arraign_month_start"] = sample.apply(_month_start, axis=1)
    sample["year_month"] = sample["arraign_month_start"].str.slice(0, 7)
    sample["post_2022_amendment"] = sample.apply(
        lambda row: _is_on_or_after(row, AMENDMENT_2022),
        axis=1,
    )
    sample["post_2023_amendment"] = sample.apply(
        lambda row: _is_on_or_after(row, AMENDMENT_2023),
        axis=1,
    )
    sample["month_index_2022_05"] = sample.apply(
        lambda row: _month_index(row, AMENDMENT_2022),
        axis=1,
    )
    sample["month_index_2023_06"] = sample.apply(
        lambda row: _month_index(row, AMENDMENT_2023),
        axis=1,
    )
    sample["charge_article"] = sample["larg_charge"].map(_charge_article)
    sample["charge_root"] = sample["larg_charge"].map(_charge_root)
    sample["charge_subdivision"] = sample["larg_charge"].map(_charge_subdivision)
    sample["any_pending_case"] = sample.apply(_any_pending_case, axis=1)
    sample["charge_exposure_2022"] = sample.apply(_charge_exposure_2022, axis=1)
    sample["charge_exposure_2023"] = sample.apply(_charge_exposure_2023, axis=1)
    sample["row_exposure_2022"] = sample.apply(_row_exposure_2022, axis=1)
    sample["row_exposure_2023"] = sample.apply(_row_exposure_2023, axis=1)
    return sample.reset_index(drop=True)


def _month_start(row: pd.Series) -> str:
    year = int(row["arraign_year"])
    month = int(row["arraign_month"])
    return f"{year:04d}-{month:02d}-01"


def _is_on_or_after(row: pd.Series, pivot: tuple[int, int]) -> bool:
    year = int(row["arraign_year"])
    month = int(row["arraign_month"])
    return (year, month) >= pivot


def _month_index(row: pd.Series, pivot: tuple[int, int]) -> int:
    year = int(row["arraign_year"])
    month = int(row["arraign_month"])
    return (year - pivot[0]) * 12 + (month - pivot[1])


def _value_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def _charge_tokens(charge: object) -> list[str]:
    text = re.sub(r"\s+", " ", str(charge or "").strip().upper())
    return text.split()


def _charge_root(charge: object) -> str:
    tokens = _charge_tokens(charge)
    if len(tokens) < 2 or tokens[0] != "PL":
        return ""
    return f"{tokens[0]} {tokens[1]}"


def _charge_subdivision(charge: object) -> str:
    tokens = _charge_tokens(charge)
    if len(tokens) < 3 or tokens[0] != "PL":
        return ""
    return tokens[2]


def _charge_article(charge: object) -> str:
    tokens = _charge_tokens(charge)
    if len(tokens) < 2 or tokens[0] != "PL":
        return ""
    return tokens[1][:3]


def _is_felony(charge_class: object) -> bool:
    return "FELONY" in str(charge_class or "").upper()


def _is_a_misdemeanor(charge_class: object) -> bool:
    return str(charge_class or "").strip().upper() == "A MISDEMEANOR"


def _is_harm_or_property_candidate(row: pd.Series) -> bool:
    article = row["charge_article"]
    return article in HARM_OR_PROPERTY_ARTICLES and (
        _is_felony(row["larg_class"]) or _is_a_misdemeanor(row["larg_class"])
    )


def _any_pending_case(row: pd.Series) -> bool:
    return any(
        str(row.get(column, "")).strip().lower() == "yes"
        for column in ["pend_vfo", "pend_nonvfo", "pend_misd"]
    )


def _charge_exposure_2022(row: pd.Series) -> str:
    charge_root = row["charge_root"]
    subdivision = row["charge_subdivision"]
    if charge_root == "PL 265.16":
        return "2022_new_qualifying_firearm_charge"
    if charge_root == "PL 265.02" and subdivision == "03":
        return "2022_new_qualifying_firearm_charge"
    if charge_root == "PL 265.01-B":
        return "2022_second_firearm_offense_charge"
    if _is_harm_or_property_candidate(row):
        return "2022_repeat_harm_or_theft_proxy_candidate"
    return "comparison"


def _charge_exposure_2023(row: pd.Series) -> str:
    if _is_harm_or_property_candidate(row):
        return "2023_repeat_offender_proxy_candidate"
    return "comparison"


def _row_exposure_2022(row: pd.Series) -> str:
    charge_exposure = row["charge_exposure_2022"]
    if charge_exposure in {
        "2022_new_qualifying_firearm_charge",
        "2022_second_firearm_offense_charge",
    }:
        return charge_exposure
    if charge_exposure == "2022_repeat_harm_or_theft_proxy_candidate" and row["any_pending_case"]:
        return "2022_repeat_harm_or_theft_proxy"
    return "comparison"


def _row_exposure_2023(row: pd.Series) -> str:
    if (
        row["charge_exposure_2023"] == "2023_repeat_offender_proxy_candidate"
        and row["any_pending_case"]
    ):
        return "2023_repeat_offender_proxy"
    return "comparison"


def _charge_exposure_template(frame: pd.DataFrame) -> pd.DataFrame:
    yearly = (
        frame.groupby(
            [
                "larg_charge",
                "larg_class",
                "larg_attempt",
                "larg_vfo",
                "larg_firearm",
                "arraign_year",
            ],
            dropna=False,
        )
        .size()
        .unstack(fill_value=0)
    )
    yearly.columns = [f"cases_{int(column)}" for column in yearly.columns]
    base = (
        frame.groupby(
            ["larg_charge", "larg_class", "larg_attempt", "larg_vfo", "larg_firearm"],
            dropna=False,
        )
        .agg(
            total_cases=("caseid", "size"),
            nyc_cases=("court_type", lambda s: int((s == "NYC Criminal Courts").sum())),
            non_nyc_cases=(
                "court_type",
                lambda s: int((s == "Non-NYC City and District Courts").sum()),
            ),
            amendment_2022_exposure=("charge_exposure_2022", "first"),
            amendment_2023_exposure=("charge_exposure_2023", "first"),
        )
        .reset_index()
    )
    merged = base.merge(
        yearly.reset_index(),
        on=["larg_charge", "larg_class", "larg_attempt", "larg_vfo", "larg_firearm"],
        how="left",
    )
    merged = merged.sort_values("total_cases", ascending=False).reset_index(drop=True)
    merged["comparison_group_candidate"] = merged.apply(_comparison_group_candidate, axis=1)
    merged["review_notes"] = merged.apply(_review_notes, axis=1)
    return merged


def _comparison_group_candidate(row: pd.Series) -> str:
    if (
        row["amendment_2022_exposure"] == "comparison"
        and row["amendment_2023_exposure"] == "comparison"
    ):
        if row["larg_firearm"] == "Not Firearm Charge" and (
            _is_a_misdemeanor(row["larg_class"]) or _is_felony(row["larg_class"])
        ):
            return "yes"
    return ""


def _review_notes(row: pd.Series) -> str:
    notes: list[str] = []
    if row["amendment_2022_exposure"] == "2022_repeat_harm_or_theft_proxy_candidate":
        notes.append("requires pending-case proxy at row level")
    if row["amendment_2023_exposure"] == "2023_repeat_offender_proxy_candidate":
        notes.append("2023 rule uses pending-case proxy at row level")
    if row["amendment_2022_exposure"] == "2022_second_firearm_offense_charge":
        notes.append("modeled from 265.01-B charge text")
    return "; ".join(notes)


def _render_policy_sample_report(
    summary: dict[str, Any],
    sample_path: Path,
    crosswalk_path: Path,
    summary_path: Path,
) -> str:
    lines = [
        "# Supplemental Pretrial Policy Sample",
        "",
        f"- policy_sample_path: {sample_path}",
        f"- charge_exposure_template_path: {crosswalk_path}",
        f"- summary_path: {summary_path}",
        f"- row_count: {summary['row_count']}",
        f"- column_count: {summary['column_count']}",
        f"- crosswalk_charge_rows: {summary['crosswalk_charge_rows']}",
        f"- post_2022_count: {summary['post_2022_count']}",
        f"- post_2023_count: {summary['post_2023_count']}",
        "",
        "## Scope",
        "",
        "- Lower courts with recognized court types only.",
        "- Main policy sample excludes Town and Village Justice Courts.",
        "- Main policy sample keeps valid month/year rows for `2021` through `2024`.",
        "- `month_index_2022_05` and `month_index_2023_06` are included "
        "for event-style models.",
        "- Charge exposure labels are populated from public-rule proxies.",
        "- Review the generated template before treating any exposure group as final.",
        "",
        "## Court type counts",
    ]
    for key, value in summary["court_type_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Year counts"])
    for key, value in summary["year_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Row exposure counts (2022)"])
    for key, value in summary["row_exposure_2022_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Row exposure counts (2023)"])
    for key, value in summary["row_exposure_2023_counts"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
