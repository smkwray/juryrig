from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from numpy import nan

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.dataset.policy_sample_supplemental_pretrial import (
    load_supplemental_pretrial_policy_sample,
)
from ny_oca_conviction.utils.io import write_json, write_markdown

WINDOW_MONTHS = 12
AMENDMENT_WINDOW_COLUMNS = [
    "policy_window",
    "window_side",
    "court_type",
    "severity_bucket",
    "total_cases",
    "release_decision_known",
    "released_count",
    "bail_set_count",
    "remand_count",
    "released_share_known",
    "bail_set_share_known",
    "remand_share_known",
]


def build_supplemental_pretrial_policy_tables() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = load_supplemental_pretrial_policy_sample()

    monthly_release = _monthly_release_table(frame)
    monthly_disposition = _monthly_disposition_table(frame)
    amendment_windows = _amendment_window_summary(frame)

    output_dir = paths.processed_supplemental_pretrial
    release_path = output_dir / "policy_monthly_release.csv"
    disposition_path = output_dir / "policy_monthly_disposition.csv"
    window_path = output_dir / "policy_amendment_windows.csv"
    summary_path = output_dir / "policy_tables_summary.json"
    report_path = paths.validation_artifacts / "supplemental_pretrial_policy_tables.md"

    monthly_release.to_csv(release_path, index=False)
    monthly_disposition.to_csv(disposition_path, index=False)
    amendment_windows.to_csv(window_path, index=False)

    summary = {
        "monthly_release_rows": int(len(monthly_release)),
        "monthly_disposition_rows": int(len(monthly_disposition)),
        "amendment_window_rows": int(len(amendment_windows)),
        "severity_buckets": sorted(monthly_release["severity_bucket"].dropna().unique().tolist()),
        "court_types": sorted(monthly_release["court_type"].dropna().unique().tolist()),
        "year_month_min": str(monthly_release["year_month"].min()),
        "year_month_max": str(monthly_release["year_month"].max()),
    }
    write_json(summary_path, summary)
    write_markdown(
        report_path,
        _render_policy_tables_report(
            summary,
            release_path,
            disposition_path,
            window_path,
            summary_path,
            amendment_windows,
        ),
    )

    return {
        "monthly_release_path": str(release_path),
        "monthly_disposition_path": str(disposition_path),
        "amendment_window_path": str(window_path),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "monthly_release_rows": summary["monthly_release_rows"],
        "monthly_disposition_rows": summary["monthly_disposition_rows"],
        "amendment_window_rows": summary["amendment_window_rows"],
    }


def _severity_bucket(frame: pd.DataFrame) -> pd.Series:
    charge_class = frame["larg_class"].fillna("")
    violent = frame["larg_vfo"].fillna("").ne("Not VFO") & frame["larg_vfo"].fillna("").ne("")
    felony = charge_class.str.contains("Felony", regex=False)
    misdemeanor = charge_class.str.contains("Misdemeanor", regex=False)
    bucket = pd.Series("other", index=frame.index, dtype="string")
    bucket = bucket.mask(felony & violent, "violent_felony")
    bucket = bucket.mask(felony & ~violent, "non_violent_felony")
    bucket = bucket.mask(misdemeanor, "misdemeanor")
    return bucket


def _monthly_release_table(frame: pd.DataFrame) -> pd.DataFrame:
    sample = frame.copy()
    sample["severity_bucket"] = _severity_bucket(sample)

    rel_decision = sample["larg_rel_decision"].fillna("")
    rel_outcome = sample["larg_rel_outcome"].fillna("")

    unknown_decision = rel_decision.eq("Unknown")
    disposed_at_arraign = rel_decision.eq("Disposed at arraign")
    release_decision_known = ~(unknown_decision | disposed_at_arraign)
    released = rel_outcome.isin(["ROR", "NMR/RUS", "BailPaid @arraign", "BailPaid w/in 1-5days"])
    not_released = rel_outcome.isin(["BailNotPaid w/in 5days", "Remanded"])

    summary = (
        sample.groupby(
            [
                "court_type",
                "year_month",
                "arraign_year",
                "arraign_month",
                "month_index_2022_05",
                "month_index_2023_06",
                "severity_bucket",
                "larg_firearm",
                "larg_vfo",
            ],
            dropna=False,
        )
        .agg(
            total_cases=("caseid", "size"),
            release_decision_known=(
                "caseid",
                lambda s: int(release_decision_known.loc[s.index].sum()),
            ),
            disposed_at_arraign=("caseid", lambda s: int(disposed_at_arraign.loc[s.index].sum())),
            unknown_release_decision=("caseid", lambda s: int(unknown_decision.loc[s.index].sum())),
            ror_count=("caseid", lambda s: int(rel_decision.loc[s.index].eq("ROR").sum())),
            nmr_rus_count=("caseid", lambda s: int(rel_decision.loc[s.index].eq("NMR/RUS").sum())),
            bail_set_count=(
                "caseid",
                lambda s: int(rel_decision.loc[s.index].eq("Bail Set").sum()),
            ),
            remand_count=("caseid", lambda s: int(rel_decision.loc[s.index].eq("Remanded").sum())),
            released_count=("caseid", lambda s: int(released.loc[s.index].sum())),
            not_released_count=("caseid", lambda s: int(not_released.loc[s.index].sum())),
            bail_paid_count=(
                "caseid",
                lambda s: int(
                    rel_outcome.loc[s.index]
                    .isin(["BailPaid @arraign", "BailPaid w/in 1-5days"])
                    .sum()
                ),
            ),
            bail_not_paid_count=(
                "caseid",
                lambda s: int(rel_outcome.loc[s.index].eq("BailNotPaid w/in 5days").sum()),
            ),
        )
        .reset_index()
    )

    known = summary["release_decision_known"].replace({0: nan})
    summary["released_share_known"] = summary["released_count"] / known
    summary["bail_set_share_known"] = summary["bail_set_count"] / known
    summary["remand_share_known"] = summary["remand_count"] / known
    return summary


def _monthly_disposition_table(frame: pd.DataFrame) -> pd.DataFrame:
    sample = frame.copy()
    sample["severity_bucket"] = _severity_bucket(sample)

    disposition = sample["disposition"].fillna("")
    conv_or_yo = disposition.isin(["Conviction", "YO Adjudication"])
    favorable = disposition.isin(
        [
            "Dismissed",
            "Other/Unknown Favorable",
            "Acquitted",
            "No True Bill",
            "Removed to Family Court",
            "Covered by/Consolidated",
        ]
    )
    pending = disposition.eq("Pending")

    summary = (
        sample.groupby(
            [
                "court_type",
                "year_month",
                "arraign_year",
                "arraign_month",
                "month_index_2022_05",
                "month_index_2023_06",
                "severity_bucket",
                "larg_firearm",
                "larg_vfo",
            ],
            dropna=False,
        )
        .agg(
            total_cases=("caseid", "size"),
            conviction_or_yo=("caseid", lambda s: int(conv_or_yo.loc[s.index].sum())),
            favorable=("caseid", lambda s: int(favorable.loc[s.index].sum())),
            pending=("caseid", lambda s: int(pending.loc[s.index].sum())),
        )
        .reset_index()
    )
    total = summary["total_cases"].replace({0: nan})
    summary["conviction_or_yo_share"] = summary["conviction_or_yo"] / total
    summary["favorable_share"] = summary["favorable"] / total
    summary["pending_share"] = summary["pending"] / total
    return summary


def _amendment_window_summary(frame: pd.DataFrame) -> pd.DataFrame:
    release = _monthly_release_table(frame)
    windows: list[pd.DataFrame] = []
    for label, column in [
        ("amendment_2022_05", "month_index_2022_05"),
        ("amendment_2023_06", "month_index_2023_06"),
    ]:
        subset = release[release[column].between(-WINDOW_MONTHS, WINDOW_MONTHS)].copy()
        if subset.empty:
            continue
        subset["policy_window"] = label
        subset["window_side"] = subset[column].apply(
            lambda value: "pre" if value < 0 else ("post" if value >= 0 else "post")
        )
        rolled = (
            subset.groupby(
                ["policy_window", "window_side", "court_type", "severity_bucket"],
                dropna=False,
            )
            .agg(
                total_cases=("total_cases", "sum"),
                release_decision_known=("release_decision_known", "sum"),
                released_count=("released_count", "sum"),
                bail_set_count=("bail_set_count", "sum"),
                remand_count=("remand_count", "sum"),
            )
            .reset_index()
        )
        known = rolled["release_decision_known"].replace({0: nan})
        rolled["released_share_known"] = rolled["released_count"] / known
        rolled["bail_set_share_known"] = rolled["bail_set_count"] / known
        rolled["remand_share_known"] = rolled["remand_count"] / known
        windows.append(rolled)
    if not windows:
        return pd.DataFrame(columns=AMENDMENT_WINDOW_COLUMNS)
    return pd.concat(windows, ignore_index=True)


def _render_policy_tables_report(
    summary: dict[str, Any],
    release_path: Path,
    disposition_path: Path,
    window_path: Path,
    summary_path: Path,
    amendment_windows: pd.DataFrame,
) -> str:
    lines = [
        "# Supplemental Pretrial Policy Tables",
        "",
        f"- monthly_release_path: {release_path}",
        f"- monthly_disposition_path: {disposition_path}",
        f"- amendment_window_path: {window_path}",
        f"- summary_path: {summary_path}",
        f"- monthly_release_rows: {summary['monthly_release_rows']}",
        f"- monthly_disposition_rows: {summary['monthly_disposition_rows']}",
        f"- amendment_window_rows: {summary['amendment_window_rows']}",
        f"- year_month_min: {summary['year_month_min']}",
        f"- year_month_max: {summary['year_month_max']}",
        "",
        "## Scope",
        "",
        "- Monthly aggregates are built from the `2021`-`2024` main policy sample.",
        "- Tables are grouped by court type, month, severity bucket, firearm flag, and VFO flag.",
        "- Amendment window summaries use +/- 12 months around `2022-05` and `2023-06`.",
        "",
        "## Amendment windows",
    ]
    preview = amendment_windows[
        ["policy_window", "window_side", "court_type", "severity_bucket", "released_share_known"]
    ].head(20)
    for _, row in preview.iterrows():
        lines.append(
            f"- {row['policy_window']} {row['window_side']} | "
            f"{row['court_type']} | {row['severity_bucket']} | "
            f"released_share_known={row['released_share_known']:.4f}"
        )
    return "\n".join(lines)
