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


def build_supplemental_pretrial_policy_effects() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = load_supplemental_pretrial_policy_sample()

    windows = _policy_exposure_windows(frame)
    diffs = _policy_exposure_diffs(windows)

    output_dir = paths.processed_supplemental_pretrial
    windows_path = output_dir / "policy_exposure_windows.csv"
    diffs_path = output_dir / "policy_exposure_diffs.csv"
    summary_path = output_dir / "policy_effects_summary.json"
    report_path = paths.validation_artifacts / "supplemental_pretrial_policy_effects.md"

    windows.to_csv(windows_path, index=False)
    diffs.to_csv(diffs_path, index=False)

    summary = {
        "window_rows": int(len(windows)),
        "diff_rows": int(len(diffs)),
        "policy_windows": sorted(windows["policy_window"].dropna().unique().tolist()),
        "court_types": sorted(windows["court_type"].dropna().unique().tolist()),
        "exposure_groups": sorted(windows["exposure_group"].dropna().unique().tolist()),
    }
    write_json(summary_path, summary)
    write_markdown(
        report_path,
        _render_policy_effects_report(summary, windows_path, diffs_path, summary_path, diffs),
    )
    return {
        "policy_exposure_windows_path": str(windows_path),
        "policy_exposure_diffs_path": str(diffs_path),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "window_rows": summary["window_rows"],
        "diff_rows": summary["diff_rows"],
    }


def _policy_exposure_windows(frame: pd.DataFrame) -> pd.DataFrame:
    windows: list[pd.DataFrame] = []
    for label, month_column, exposure_column in [
        ("amendment_2022_05", "month_index_2022_05", "row_exposure_2022"),
        ("amendment_2023_06", "month_index_2023_06", "row_exposure_2023"),
    ]:
        subset = frame[frame[month_column].between(-WINDOW_MONTHS, WINDOW_MONTHS)].copy()
        if subset.empty:
            continue
        subset["policy_window"] = label
        subset["window_side"] = subset[month_column].apply(
            lambda value: "pre" if value < 0 else "post"
        )
        subset["exposure_group"] = subset[exposure_column]

        rel_decision = subset["larg_rel_decision"].fillna("")
        rel_outcome = subset["larg_rel_outcome"].fillna("")
        disposition = subset["disposition"].fillna("")

        release_decision_known = ~rel_decision.isin(["Unknown", "Disposed at arraign"])
        released = rel_outcome.isin(
            ["ROR", "NMR/RUS", "BailPaid @arraign", "BailPaid w/in 1-5days"]
        )
        bail_set = rel_decision.eq("Bail Set")
        remand = rel_decision.eq("Remanded")
        conviction_or_yo = disposition.isin(["Conviction", "YO Adjudication"])
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

        grouped = (
            subset.groupby(
                ["policy_window", "window_side", "court_type", "exposure_group"],
                dropna=False,
            )
            .agg(
                total_cases=("caseid", "size"),
                release_decision_known=(
                    "caseid",
                    lambda s, mask=release_decision_known: int(mask.loc[s.index].sum()),
                ),
                released_count=("caseid", lambda s, mask=released: int(mask.loc[s.index].sum())),
                bail_set_count=("caseid", lambda s, mask=bail_set: int(mask.loc[s.index].sum())),
                remand_count=("caseid", lambda s, mask=remand: int(mask.loc[s.index].sum())),
                conviction_or_yo=(
                    "caseid",
                    lambda s, mask=conviction_or_yo: int(mask.loc[s.index].sum()),
                ),
                favorable=("caseid", lambda s, mask=favorable: int(mask.loc[s.index].sum())),
                pending=("caseid", lambda s, mask=pending: int(mask.loc[s.index].sum())),
            )
            .reset_index()
        )
        known = grouped["release_decision_known"].replace({0: nan})
        total = grouped["total_cases"].replace({0: nan})
        grouped["released_share_known"] = grouped["released_count"] / known
        grouped["bail_set_share_known"] = grouped["bail_set_count"] / known
        grouped["remand_share_known"] = grouped["remand_count"] / known
        grouped["conviction_or_yo_share"] = grouped["conviction_or_yo"] / total
        grouped["favorable_share"] = grouped["favorable"] / total
        grouped["pending_share"] = grouped["pending"] / total
        windows.append(grouped)

    if not windows:
        return pd.DataFrame()
    return pd.concat(windows, ignore_index=True)


def _policy_exposure_diffs(windows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (policy_window, court_type), group in windows.groupby(
        ["policy_window", "court_type"],
        dropna=False,
    ):
        grouped = {
            exposure_group: exposure_rows.set_index("window_side")
            for exposure_group, exposure_rows in group.groupby("exposure_group", dropna=False)
        }
        if "comparison" not in grouped:
            continue
        comparison = grouped["comparison"]
        if not {"pre", "post"}.issubset(comparison.index):
            continue
        for exposure_group, exposure in grouped.items():
            if exposure_group == "comparison":
                continue
            if not {"pre", "post"}.issubset(exposure.index):
                continue
            exposure_pre = exposure.loc["pre"]
            exposure_post = exposure.loc["post"]
            comparison_pre = comparison.loc["pre"]
            comparison_post = comparison.loc["post"]
            rows.append(
                {
                    "policy_window": policy_window,
                    "court_type": court_type,
                    "exposure_group": exposure_group,
                    "exposed_pre_released_share_known": exposure_pre["released_share_known"],
                    "exposed_post_released_share_known": exposure_post["released_share_known"],
                    "comparison_pre_released_share_known": comparison_pre["released_share_known"],
                    "comparison_post_released_share_known": comparison_post["released_share_known"],
                    "exposed_delta_released_share_known": (
                        exposure_post["released_share_known"] - exposure_pre["released_share_known"]
                    ),
                    "comparison_delta_released_share_known": (
                        comparison_post["released_share_known"]
                        - comparison_pre["released_share_known"]
                    ),
                    "diff_vs_comparison_released_share_known": (
                        (
                            exposure_post["released_share_known"]
                            - exposure_pre["released_share_known"]
                        )
                        - (
                            comparison_post["released_share_known"]
                            - comparison_pre["released_share_known"]
                        )
                    ),
                    "exposed_delta_conviction_or_yo_share": (
                        exposure_post["conviction_or_yo_share"]
                        - exposure_pre["conviction_or_yo_share"]
                    ),
                    "comparison_delta_conviction_or_yo_share": (
                        comparison_post["conviction_or_yo_share"]
                        - comparison_pre["conviction_or_yo_share"]
                    ),
                    "diff_vs_comparison_conviction_or_yo_share": (
                        (
                            exposure_post["conviction_or_yo_share"]
                            - exposure_pre["conviction_or_yo_share"]
                        )
                        - (
                            comparison_post["conviction_or_yo_share"]
                            - comparison_pre["conviction_or_yo_share"]
                        )
                    ),
                }
            )
    return pd.DataFrame(rows)


def _render_policy_effects_report(
    summary: dict[str, Any],
    windows_path: Path,
    diffs_path: Path,
    summary_path: Path,
    diffs: pd.DataFrame,
) -> str:
    lines = [
        "# Supplemental Pretrial Policy Effects",
        "",
        f"- policy_exposure_windows_path: {windows_path}",
        f"- policy_exposure_diffs_path: {diffs_path}",
        f"- summary_path: {summary_path}",
        f"- window_rows: {summary['window_rows']}",
        f"- diff_rows: {summary['diff_rows']}",
        "",
        "## Scope",
        "",
        "- 2022 window uses charge-based firearm additions and a repeat-offender proxy.",
        "- 2023 window uses a repeat-offender proxy based on pending-case indicators.",
        "- Window summaries cover +/- 12 months around May 2022 and June 2023.",
        "",
        "## Diff summary preview",
    ]
    preview = diffs.head(20)
    for _, row in preview.iterrows():
        lines.append(
            f"- {row['policy_window']} | {row['court_type']} | {row['exposure_group']} | "
            f"release_diff_vs_comparison={row['diff_vs_comparison_released_share_known']:.4f} | "
            f"conviction_diff_vs_comparison={row['diff_vs_comparison_conviction_or_yo_share']:.4f}"
        )
    return "\n".join(lines)
