from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.normalize_supplemental_pretrial import load_raw_supplemental_pretrial
from ny_oca_conviction.utils.io import write_json, write_markdown

COURT_TYPE_MAP = {
    "NYC Criminal Court": "NYC Criminal Courts",
    "Non-NYC City or District Court": "Non-NYC City and District Courts",
    "Non-NYC Town or Village Justice Court": "Non-NYC Town and Village Justice Courts",
}

OFFICIAL_TABLE1_ROWS = [
    ("NYC Criminal Courts", "2019", 142949, 111346, 27816, 3787),
    ("NYC Criminal Courts", "2020", 82502, 73090, 9203, 209),
    ("NYC Criminal Courts", "2021", 106265, 89264, 16616, 385),
    ("NYC Criminal Courts", "2022", 125395, 103501, 21539, 355),
    ("NYC Criminal Courts", "2023", 144927, 118423, 26108, 396),
    ("NYC Criminal Courts", "2024", 164600, 133398, 30822, 380),
    ("Non-NYC City and District Courts", "2019", 90488, 84687, 4966, 835),
    ("Non-NYC City and District Courts", "2020", 65773, 60159, 3380, 2234),
    ("Non-NYC City and District Courts", "2021", 70878, 64766, 4030, 2082),
    ("Non-NYC City and District Courts", "2022", 75485, 69411, 4573, 1501),
    ("Non-NYC City and District Courts", "2023", 81612, 75914, 4329, 1369),
    ("Non-NYC City and District Courts", "2024", 84814, 79064, 4664, 1086),
    ("Non-NYC Town and Village Justice Courts", "2023(6M)", 36196, 28883, 4130, 3183),
    ("Non-NYC Town and Village Justice Courts", "2024", 68912, 53316, 8453, 7143),
]

OFFICIAL_TABLE9_ROWS = [
    ("NYC Criminal Courts", "2019", 142949, 62953, 76832, 3164),
    ("NYC Criminal Courts", "2020", 82502, 23986, 56907, 1609),
    ("NYC Criminal Courts", "2021", 106265, 29370, 74781, 2114),
    ("NYC Criminal Courts", "2022", 125395, 36865, 84955, 3575),
    ("NYC Criminal Courts", "2023", 144927, 39858, 97802, 7267),
    ("NYC Criminal Courts", "2024", 164600, 38935, 108472, 17193),
    ("Non-NYC City and District Courts", "2019", 90488, 54143, 34191, 2154),
    ("Non-NYC City and District Courts", "2020", 65773, 34434, 28690, 2649),
    ("Non-NYC City and District Courts", "2021", 70878, 38104, 30010, 2764),
    ("Non-NYC City and District Courts", "2022", 75485, 40187, 32090, 3208),
    ("Non-NYC City and District Courts", "2023", 81612, 40434, 34780, 6398),
    ("Non-NYC City and District Courts", "2024", 84814, 36015, 31180, 17619),
    ("Non-NYC Town and Village Justice Courts", "2023(6M)", 36196, 19901, 11818, 4477),
    ("Non-NYC Town and Village Justice Courts", "2024", 68912, 34116, 19114, 15682),
]


def replicate_supplemental_pretrial_tables() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = load_raw_supplemental_pretrial()
    sample = _official_sample(frame)

    table1_computed = _table1_annual(sample)
    table1_official = _official_table1()
    table1_compare = _compare_tables(
        table1_computed,
        table1_official,
        metric_columns=[
            "total_arraignments",
            "release_decisions",
            "disposed_at_arraignment",
            "unknown_release_decisions",
        ],
    )

    table9_computed = _table9_annual(sample)
    table9_official = _official_table9()
    table9_compare = _compare_tables(
        table9_computed,
        table9_official,
        metric_columns=[
            "total_arraignments",
            "conviction_or_yo",
            "dismissed_or_other_favorable",
            "pending",
        ],
    )

    output_dir = paths.processed_supplemental_pretrial
    table1_computed_path = output_dir / "table1_annual_computed.csv"
    table1_compare_path = output_dir / "table1_annual_comparison.csv"
    table9_computed_path = output_dir / "table9_annual_computed.csv"
    table9_compare_path = output_dir / "table9_annual_comparison.csv"
    report_path = paths.validation_artifacts / "supplemental_pretrial_replication.md"
    summary_path = output_dir / "replication_summary.json"

    table1_computed.to_csv(table1_computed_path, index=False)
    table1_compare.to_csv(table1_compare_path, index=False)
    table9_computed.to_csv(table9_computed_path, index=False)
    table9_compare.to_csv(table9_compare_path, index=False)

    summary = {
        "sample_row_count": int(len(sample)),
        "table1_rows": int(len(table1_compare)),
        "table1_all_match": bool(table1_compare["all_metrics_match"].all()),
        "table9_rows": int(len(table9_compare)),
        "table9_all_match": bool(table9_compare["all_metrics_match"].all()),
    }
    write_json(summary_path, summary)
    write_markdown(
        report_path,
        _render_report(
            summary,
            table1_compare,
            table9_compare,
            table1_computed_path,
            table1_compare_path,
            table9_computed_path,
            table9_compare_path,
        ),
    )

    return {
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "table1_computed_path": str(table1_computed_path),
        "table1_compare_path": str(table1_compare_path),
        "table9_computed_path": str(table9_computed_path),
        "table9_compare_path": str(table9_compare_path),
        "sample_row_count": summary["sample_row_count"],
        "table1_all_match": summary["table1_all_match"],
        "table9_all_match": summary["table9_all_match"],
    }


def _official_sample(frame: pd.DataFrame) -> pd.DataFrame:
    sample = frame[frame["larg_court_type"].isin(COURT_TYPE_MAP)].copy()
    sample = sample[sample["larg_yr"].isin(["2019", "2020", "2021", "2022", "2023", "2024"])].copy()
    sample["court_type"] = sample["larg_court_type"].map(COURT_TYPE_MAP)
    sample["year_label"] = sample["larg_yr"]
    sample.loc[
        (sample["court_type"] == "Non-NYC Town and Village Justice Courts")
        & (sample["larg_yr"] == "2023"),
        "year_label",
    ] = "2023(6M)"
    return sample


def _table1_annual(frame: pd.DataFrame) -> pd.DataFrame:
    rel = frame["larg_rel_decision"].fillna("")
    unknown = rel.isin(["", "Unknown"])
    disposed = rel.eq("Disposed at arraign")
    release = ~(unknown | disposed)
    summary = (
        frame.groupby(["court_type", "year_label"])
        .agg(
            total_arraignments=("caseid", "size"),
            release_decisions=("caseid", lambda s: int(release.loc[s.index].sum())),
            disposed_at_arraignment=("caseid", lambda s: int(disposed.loc[s.index].sum())),
            unknown_release_decisions=("caseid", lambda s: int(unknown.loc[s.index].sum())),
        )
        .reset_index()
    )
    return summary


def _table9_annual(frame: pd.DataFrame) -> pd.DataFrame:
    conv_or_yo = frame["disposition"].isin(["Conviction", "YO Adjudication"])
    favorable = frame["disposition"].isin(
        [
            "Dismissed",
            "Other/Unknown Favorable",
            "Acquitted",
            "No True Bill",
            "Removed to Family Court",
            "Covered by/Consolidated",
        ]
    )
    pending = frame["disposition"].eq("Pending")
    summary = (
        frame.groupby(["court_type", "year_label"])
        .agg(
            total_arraignments=("caseid", "size"),
            conviction_or_yo=("caseid", lambda s: int(conv_or_yo.loc[s.index].sum())),
            dismissed_or_other_favorable=("caseid", lambda s: int(favorable.loc[s.index].sum())),
            pending=("caseid", lambda s: int(pending.loc[s.index].sum())),
        )
        .reset_index()
    )
    return summary


def _official_table1() -> pd.DataFrame:
    return pd.DataFrame(
        OFFICIAL_TABLE1_ROWS,
        columns=[
            "court_type",
            "year_label",
            "total_arraignments",
            "release_decisions",
            "disposed_at_arraignment",
            "unknown_release_decisions",
        ],
    )


def _official_table9() -> pd.DataFrame:
    return pd.DataFrame(
        OFFICIAL_TABLE9_ROWS,
        columns=[
            "court_type",
            "year_label",
            "total_arraignments",
            "conviction_or_yo",
            "dismissed_or_other_favorable",
            "pending",
        ],
    )


def _compare_tables(
    computed: pd.DataFrame,
    official: pd.DataFrame,
    metric_columns: list[str],
) -> pd.DataFrame:
    merged = computed.merge(
        official,
        on=["court_type", "year_label"],
        suffixes=("_computed", "_official"),
        how="outer",
    )
    for column in metric_columns:
        merged[f"{column}_delta"] = (
            merged[f"{column}_computed"].fillna(0).astype(int)
            - merged[f"{column}_official"].fillna(0).astype(int)
        )
        merged[f"{column}_match"] = merged[f"{column}_delta"].eq(0)
    merged["all_metrics_match"] = merged[[f"{column}_match" for column in metric_columns]].all(
        axis=1
    )
    return merged.sort_values(["court_type", "year_label"]).reset_index(drop=True)


def _render_report(
    summary: dict[str, Any],
    table1_compare: pd.DataFrame,
    table9_compare: pd.DataFrame,
    table1_computed_path: Path,
    table1_compare_path: Path,
    table9_computed_path: Path,
    table9_compare_path: Path,
) -> str:
    lines = [
        "# Supplemental Pretrial Replication",
        "",
        f"- sample_row_count: {summary['sample_row_count']}",
        f"- table1_all_match: {summary['table1_all_match']}",
        f"- table9_all_match: {summary['table9_all_match']}",
        f"- table1_computed_path: {table1_computed_path}",
        f"- table1_compare_path: {table1_compare_path}",
        f"- table9_computed_path: {table9_computed_path}",
        f"- table9_compare_path: {table9_compare_path}",
        "",
        "## Scope",
        "",
        "- Official-style sample: recognized lower-court types only, "
        "arraignment years `2019`-`2024`.",
        "- Town and Village `2023` rows are labeled `2023(6M)` to match "
        "the published summary tables.",
        "- Table 9 favorable outcomes include `Covered by/Consolidated` "
        "to match the published totals.",
        "",
        "## Table 1",
    ]
    for _, row in table1_compare.iterrows():
        lines.append(
            f"- {row['court_type']} {row['year_label']}: "
            f"{'match' if row['all_metrics_match'] else 'mismatch'}"
        )
    lines.extend(["", "## Table 9"])
    for _, row in table9_compare.iterrows():
        lines.append(
            f"- {row['court_type']} {row['year_label']}: "
            f"{'match' if row['all_metrics_match'] else 'mismatch'}"
        )
    return "\n".join(lines)
