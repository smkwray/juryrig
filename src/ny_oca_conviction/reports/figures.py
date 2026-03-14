from __future__ import annotations

import math
from typing import Any

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.utils.io import ensure_directory, read_json, write_json

PLOT_WIDTH = 920
PLOT_HEIGHT = 560
PLOT_BG = "#f7f3ea"
PLOT_PANEL = "#fffdf8"
TEXT_DARK = "#1f2933"
TEXT_MID = "#52606d"
GRID = "#d9d3c7"
BLUE = "#33658a"
TEAL = "#2f8f9d"
GOLD = "#f4a259"
RED = "#c8553d"
GREEN = "#6a994e"
SLATE = "#7b8794"


def build_public_figures(run_id: str = "20260307_224037") -> dict[str, Any]:
    paths = ensure_project_layout()
    figures_dir = ensure_directory(paths.root / "docs" / "figures")

    metrics = read_json(paths.runs / run_id / "metrics.json")
    subgroup = pd.read_csv(paths.runs / run_id / "subgroup_audit.csv")
    county = pd.read_csv(paths.runs / run_id / "county_transfer.csv")
    exposure_diffs = pd.read_csv(
        paths.processed_supplemental_pretrial / "policy_exposure_diffs.csv"
    )
    monthly_release = pd.read_csv(
        paths.processed_supplemental_pretrial / "policy_monthly_release.csv"
    )
    policy_summary = read_json(
        paths.processed_supplemental_pretrial / "policy_sample_summary.json"
    )
    race_association = read_json(
        paths.validation_artifacts / "race_adjusted_association.json"
    )

    outputs = {
        "predictive_metrics": figures_dir / "predictive_metrics.svg",
        "race_subgroup_auroc": figures_dir / "race_subgroup_auroc.svg",
        "race_conviction_rates": figures_dir / "race_conviction_rates.svg",
        "race_adjusted_gaps": figures_dir / "race_adjusted_gaps.svg",
        "county_extremes_auroc": figures_dir / "county_extremes_auroc.svg",
        "supplemental_pretrial_release_diffs": (
            figures_dir / "supplemental_pretrial_release_diffs.svg"
        ),
        "supplemental_pretrial_release_trends": (
            figures_dir / "supplemental_pretrial_release_trends.svg"
        ),
    }

    outputs["predictive_metrics"].write_text(
        _render_predictive_metrics_svg(metrics),
        encoding="utf-8",
    )
    outputs["race_subgroup_auroc"].write_text(
        _render_race_subgroup_svg(subgroup),
        encoding="utf-8",
    )
    outputs["race_conviction_rates"].write_text(
        _render_race_positive_rate_svg(subgroup),
        encoding="utf-8",
    )
    outputs["race_adjusted_gaps"].write_text(
        _render_race_adjusted_gap_svg(race_association),
        encoding="utf-8",
    )
    outputs["county_extremes_auroc"].write_text(
        _render_county_extremes_svg(county),
        encoding="utf-8",
    )
    outputs["supplemental_pretrial_release_diffs"].write_text(
        _render_pretrial_release_diffs_svg(exposure_diffs, policy_summary),
        encoding="utf-8",
    )
    outputs["supplemental_pretrial_release_trends"].write_text(
        _render_pretrial_release_trend_svg(monthly_release, policy_summary),
        encoding="utf-8",
    )

    manifest_path = figures_dir / "manifest.json"
    payload = {
        "run_id": run_id,
        "figures": {
            key: str(path.relative_to(paths.root))
            for key, path in outputs.items()
        },
    }
    write_json(manifest_path, payload)
    payload["manifest_path"] = str(manifest_path.relative_to(paths.root))
    return payload


def _render_predictive_metrics_svg(metrics: dict[str, Any]) -> str:
    models = ["dummy", "logistic_regression", "hist_gradient_boosting"]
    labels = {
        "dummy": "Dummy",
        "logistic_regression": "Logistic",
        "hist_gradient_boosting": "Hist GB",
    }
    colors = {
        "dummy": SLATE,
        "logistic_regression": TEAL,
        "hist_gradient_boosting": BLUE,
    }
    values = metrics["models"]
    aurocs = {name: float(values[name]["auroc"]) for name in models}
    pr_aucs = {name: float(values[name]["pr_auc"]) for name in models}
    briers = {name: float(values[name]["brier_score"]) for name in models}

    left = 160
    height = 450
    top = 136
    bar_width = 300
    row_gap = 80
    bar_height = 24
    panel_right = 870

    parts = [_svg_start("Predictive model comparison", height=height)]
    parts.append(_panel(height=height))
    parts.append(
        _title("Predictive branch: model comparison", "Reference run 20260307_224037")
    )
    parts.append(
        _text(
            left,
            100,
            "AUROC bars show ranking quality. PR-AUC and Brier are listed at right.",
            18,
            TEXT_MID,
        )
    )

    for idx, model in enumerate(models):
        y = top + idx * row_gap
        parts.append(_text(44, y + 18, labels[model], 22, TEXT_DARK, weight="700"))
        parts.append(_rect(left, y, bar_width, bar_height, "#e9e4da"))
        parts.append(_rect(left, y, bar_width * aurocs[model], bar_height, colors[model]))
        parts.append(
            _text(
                left + bar_width + 16,
                y + 18,
                f"AUROC {aurocs[model]:.3f}",
                18,
                TEXT_DARK,
            )
        )
        parts.append(_text(panel_right - 180, y + 8, f"PR-AUC {pr_aucs[model]:.3f}", 18, TEXT_MID))
        parts.append(_text(panel_right - 180, y + 30, f"Brier {briers[model]:.3f}", 18, TEXT_MID))

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = left + bar_width * tick
        parts.append(_line(x, top - 20, x, top + row_gap * 3 - 36, GRID, 1))
        parts.append(_text(x - 10, top + row_gap * 3 - 6, f"{tick:.2f}", 14, TEXT_MID))

    parts.append(
        _footnote(
            "Higher AUROC / PR-AUC is better. Lower Brier is better.",
            y=412,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_race_subgroup_svg(subgroup: pd.DataFrame) -> str:
    race = subgroup[subgroup["column"] == "Race"].copy().sort_values("auroc", ascending=True)
    height = 500
    left = 210
    top = 132
    bar_width = 400
    row_gap = 52
    bar_height = 24
    min_auroc = 0.5
    max_auroc = max(0.8, math.ceil(float(race["auroc"].max()) * 100) / 100)

    parts = [_svg_start("Predictive branch race subgroup AUROC", height=height)]
    parts.append(_panel(height=height))
    parts.append(_title("Race subgroup AUROC", "Predictive branch test split"))
    parts.append(
        _text(
            left,
            100,
            "Bar length shows AUROC. Labels at right show Brier score.",
            18,
            TEXT_MID,
        )
    )

    for idx, row in enumerate(race.itertuples(index=False)):
        y = top + idx * row_gap
        parts.append(_text(52, y + 19, str(row.value), 20, TEXT_DARK, weight="700"))
        parts.append(_text(118, y + 19, f"n={int(row.row_count):,}", 14, TEXT_MID))
        parts.append(_rect(left, y, bar_width, bar_height, "#e9e4da"))
        value_x = _scale_value(float(row.auroc), min_auroc, max_auroc, left, left + bar_width)
        parts.append(_rect(left, y, value_x - left, bar_height, GOLD))
        parts.append(
            _text(
                left + bar_width + 18,
                y + 10,
                f"AUROC {float(row.auroc):.3f}",
                16,
                TEXT_DARK,
            )
        )
        parts.append(
            _text(
                left + bar_width + 18,
                y + 28,
                f"Brier {float(row.brier_score):.3f}",
                15,
                TEXT_MID,
            )
        )

    for tick in [0.5, 0.6, 0.7, 0.8]:
        x = _scale_value(tick, min_auroc, max_auroc, left, left + bar_width)
        parts.append(_line(x, top - 20, x, top + row_gap * len(race) - 26, GRID, 1))
        parts.append(_text(x - 10, top + row_gap * len(race) + 6, f"{tick:.1f}", 14, TEXT_MID))

    parts.append(
        _footnote(
            "This chart shows model performance differences across race groups "
            "in the current test split.",
            y=470,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_county_extremes_svg(county: pd.DataFrame) -> str:
    ranked = county.sort_values("auroc", ascending=False)
    top = ranked.head(3).copy()
    bottom = ranked.tail(3).copy().sort_values("auroc", ascending=True)
    frame = pd.concat([top, bottom], ignore_index=True)
    height = 500
    left = 230
    top_y = 132
    bar_width = 460
    row_gap = 52
    bar_height = 24
    min_auroc = 0.5
    max_auroc = max(0.8, math.ceil(float(frame["auroc"].max()) * 100) / 100)

    parts = [_svg_start("County AUROC extremes", height=height)]
    parts.append(_panel(height=height))
    parts.append(
        _title(
            "County AUROC: highest and lowest examples",
            "Predictive branch county transfer check",
        )
    )
    parts.append(
        _text(
            left,
            100,
            "Examples only. Counties differ in sample size, so this is not a league table.",
            18,
            TEXT_MID,
        )
    )

    for idx, row in enumerate(frame.itertuples(index=False)):
        y = top_y + idx * row_gap
        color = BLUE if idx < 3 else RED
        parts.append(_text(44, y + 18, str(row.County), 20, TEXT_DARK, weight="700"))
        parts.append(_text(132, y + 18, f"n={int(row.row_count):,}", 14, TEXT_MID))
        parts.append(_rect(left, y, bar_width, bar_height, "#e9e4da"))
        value_x = _scale_value(float(row.auroc), min_auroc, max_auroc, left, left + bar_width)
        parts.append(_rect(left, y, value_x - left, bar_height, color))
        parts.append(
            _text(
                left + bar_width + 18,
                y + 18,
                f"AUROC {float(row.auroc):.3f}",
                18,
                TEXT_DARK,
            )
        )

    for tick in [0.5, 0.6, 0.7, 0.8]:
        x = _scale_value(tick, min_auroc, max_auroc, left, left + bar_width)
        parts.append(_line(x, top_y - 20, x, top_y + row_gap * len(frame) - 30, GRID, 1))
        parts.append(_text(x - 10, top_y + row_gap * len(frame) + 6, f"{tick:.1f}", 14, TEXT_MID))

    parts.append(
        _footnote(
            "Top examples: Monroe, Queens, Orange. Lower examples: "
            "Schoharie, Franklin, Cortland.",
            y=470,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_race_positive_rate_svg(subgroup: pd.DataFrame) -> str:
    race = (
        subgroup[subgroup["column"] == "Race"]
        .copy()
        .sort_values("positive_rate", ascending=True)
    )
    overall_rate = float(
        (race["row_count"] * race["positive_rate"]).sum() / race["row_count"].sum()
    )
    height = 500
    left = 210
    top = 132
    bar_width = 400
    row_gap = 52
    bar_height = 24
    min_rate = 0.0
    max_rate = max(0.7, math.ceil(float(race["positive_rate"].max()) * 10) / 10)

    parts = [_svg_start("Observed conviction rate by race", height=height)]
    parts.append(_panel(height=height))
    parts.append(_title("Observed conviction rate by race", "Predictive branch test split"))
    parts.append(
        _text(
            left,
            100,
            "This is the observed conviction share in the labeled test data, not model accuracy.",
            18,
            TEXT_MID,
        )
    )

    overall_x = _scale_value(overall_rate, min_rate, max_rate, left, left + bar_width)
    parts.append(_line(overall_x, top - 20, overall_x, top + row_gap * len(race) - 26, RED, 2))

    for idx, row in enumerate(race.itertuples(index=False)):
        y = top + idx * row_gap
        value_x = _scale_value(float(row.positive_rate), min_rate, max_rate, left, left + bar_width)
        parts.append(_text(52, y + 19, str(row.value), 20, TEXT_DARK, weight="700"))
        parts.append(_text(118, y + 19, f"n={int(row.row_count):,}", 14, TEXT_MID))
        parts.append(_rect(left, y, bar_width, bar_height, "#e9e4da"))
        parts.append(_rect(left, y, value_x - left, bar_height, BLUE))
        parts.append(
            _text(
                left + bar_width + 18,
                y + 18,
                f"{float(row.positive_rate):.1%}",
                18,
                TEXT_DARK,
            )
        )

    for tick in [0.0, 0.2, 0.4, 0.6]:
        x = _scale_value(tick, min_rate, max_rate, left, left + bar_width)
        parts.append(_line(x, top - 20, x, top + row_gap * len(race) - 26, GRID, 1))
        parts.append(_text(x - 12, top + row_gap * len(race) + 6, f"{tick:.1f}", 14, TEXT_MID))

    parts.append(_text(overall_x + 10, 118, f"Overall {overall_rate:.1%}", 16, RED))
    parts.append(
        _footnote(
            "Higher values mean a larger share of cases ended in conviction in this test cohort.",
            y=470,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_pretrial_release_diffs_svg(
    diffs: pd.DataFrame,
    policy_summary: dict[str, Any],
) -> str:
    frame = diffs.copy()
    frame["label"] = frame.apply(_exposure_label, axis=1)
    frame["court_short"] = frame["court_type"].map(
        {
            "NYC Criminal Courts": "NYC",
            "Non-NYC City and District Courts": "Non-NYC",
        }
    )
    frame = frame.sort_values("diff_vs_comparison_released_share_known")

    height = 620
    left = 350
    top = 136
    row_gap = 54
    bar_height = 22
    half_width = 210
    max_abs = max(
        abs(float(frame["diff_vs_comparison_released_share_known"].min())),
        abs(float(frame["diff_vs_comparison_released_share_known"].max())),
        0.05,
    )
    bound = max(0.35, _round_up_to_step(max_abs, 0.05))
    min_value = -bound
    max_value = bound
    center_x = _scale_value(0.0, min_value, max_value, left, left + half_width * 2)

    parts = [_svg_start("Supplemental pretrial release-rate differences", height=height)]
    parts.append(_panel(height=height))
    parts.append(
        _title(
            "Supplemental pretrial: release-rate change vs comparison group",
            "Pre/post window differences around the amendment dates",
        )
    )
    parts.append(
        _text(
            60,
            100,
            (
                f"Main policy sample: {int(policy_summary['row_count']):,} cases. "
                "Bars left of center mean a larger drop than the comparison group."
            ),
            17,
            TEXT_MID,
        )
    )
    parts.append(_line(center_x, top - 24, center_x, top + row_gap * len(frame) - 26, TEXT_MID, 2))

    for idx, row in enumerate(frame.itertuples(index=False)):
        y = top + idx * row_gap
        value = float(row.diff_vs_comparison_released_share_known)
        x = _scale_value(value, min_value, max_value, left, left + half_width * 2)
        width = abs(x - center_x)
        bar_x = min(x, center_x)
        color = RED if value < 0 else GREEN
        parts.append(
            _text(
                42,
                y + 16,
                f"{row.court_short} {row.label}",
                18,
                TEXT_DARK,
                weight="700",
            )
        )
        parts.append(_rect(left, y, half_width * 2, bar_height, "#efe8dc"))
        parts.append(_rect(bar_x, y, width, bar_height, color))
        parts.append(
            _text(left + half_width * 2 + 18, y + 16, f"{value:+.3f}", 18, TEXT_DARK)
        )

    tick_step = 0.1 if bound > 0.2 else 0.05
    tick_limit = math.floor(bound / tick_step) * tick_step
    ticks = [
        -tick_limit,
        -(tick_limit / 2),
        0.0,
        tick_limit / 2,
        tick_limit,
    ]
    for tick in ticks:
        x = _scale_value(tick, min_value, max_value, left, left + half_width * 2)
        parts.append(_line(x, top - 24, x, top + row_gap * len(frame) - 26, GRID, 1))
        parts.append(
            _text(x - 14, top + row_gap * len(frame) + 10, f"{tick:+.2f}", 14, TEXT_MID)
        )

    parts.append(
        _footnote(
            "Negative values mean the targeted group's release rate fell more "
            "than the comparison group over the same window.",
            y=590,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_race_adjusted_gap_svg(payload: dict[str, Any]) -> str:
    models = [
        ("core_adjusted", "Core adjusted", BLUE),
        ("charge_detail_adjusted", "Charge detail", TEAL),
        ("matched_strata", "Matched strata", GOLD),
    ]
    rows: list[dict[str, Any]] = []
    for entry in payload["adjusted_models"]["core_adjusted"]["standardized_probability_table"]:
        race = str(entry["race"])
        if race == payload["reference_race"]:
            continue
        row = {"race": race}
        for model_key, _, _ in models[:2]:
            model_rows = payload["adjusted_models"][model_key]["standardized_probability_table"]
            match = next(item for item in model_rows if str(item["race"]) == race)
            row[model_key] = float(match["diff_vs_white_pp"])
        matched_rows = payload["matched_strata"]["comparisons"]
        matched_match = next(item for item in matched_rows if str(item["race"]) == race)
        row["matched_strata"] = float(matched_match["weighted_diff_vs_white_pp"])
        rows.append(row)

    frame = pd.DataFrame(rows).sort_values("charge_detail_adjusted")
    height = 560
    left = 260
    top = 142
    row_gap = 70
    bar_height = 14
    plot_width = 430
    min_value = min(
        -1.0,
        float(frame[[model_key for model_key, _, _ in models]].min().min()) - 0.5,
    )
    max_value = 2.0
    min_value = math.floor(min_value)
    center_x = _scale_value(0.0, min_value, max_value, left, left + plot_width)

    parts = [_svg_start("Adjusted race gaps vs White defendants", height=height)]
    parts.append(_panel(height=height))
    parts.append(
        _title(
            "Adjusted race gaps vs White defendants",
            "Difference in conviction probability, percentage points",
        )
    )
    parts.append(
        _text(
            54,
            100,
            (
                "Negative values mean a lower adjusted conviction rate than "
                "otherwise similar White cases."
            ),
            17,
            TEXT_MID,
        )
    )
    parts.append(_line(center_x, top - 24, center_x, top + row_gap * len(frame) - 22, TEXT_MID, 2))

    offsets = [-18, 0, 18]
    for idx, row in enumerate(frame.itertuples(index=False)):
        base_y = top + idx * row_gap
        parts.append(_text(46, base_y + 10, str(row.race), 20, TEXT_DARK, weight="700"))
        for offset, (model_key, _label, color) in zip(offsets, models, strict=True):
            value = float(getattr(row, model_key))
            y = base_y + offset
            x = _scale_value(value, min_value, max_value, left, left + plot_width)
            bar_x = min(x, center_x)
            width = abs(x - center_x)
            parts.append(_rect(left, y, plot_width, bar_height, "#efe8dc"))
            parts.append(_rect(bar_x, y, width, bar_height, color))
            parts.append(
                _text(
                    left + plot_width + 18,
                    y + 12,
                    f"{value:+.1f} pp",
                    16,
                    TEXT_DARK,
                )
            )

    for tick in range(int(min_value), int(max_value) + 1, 2):
        x = _scale_value(float(tick), min_value, max_value, left, left + plot_width)
        parts.append(_line(x, top - 24, x, top + row_gap * len(frame) - 22, GRID, 1))
        parts.append(_text(x - 14, top + row_gap * len(frame) + 8, f"{tick:+d}", 14, TEXT_MID))

    legend_y = 474
    legend_x = 62
    for idx, (_, label, color) in enumerate(models):
        x = legend_x + idx * 185
        parts.append(_rect(x, legend_y, 22, 12, color))
        parts.append(_text(x + 32, legend_y + 11, label, 16, TEXT_DARK))

    parts.append(
        _footnote(
            (
                "These are adjusted associations, not causal effects. White is the "
                "reference group in all three methods."
            ),
            y=530,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _render_pretrial_release_trend_svg(
    monthly_release: pd.DataFrame,
    policy_summary: dict[str, Any],
) -> str:
    frame = (
        monthly_release.groupby(["year_month", "court_type"], as_index=False)[
            ["released_count", "release_decision_known"]
        ]
        .sum()
        .assign(
            released_share_known=lambda df: (
                df["released_count"] / df["release_decision_known"]
            )
        )
        .sort_values(["year_month", "court_type"])
    )
    months = sorted(frame["year_month"].unique())
    month_index = {month: idx for idx, month in enumerate(months)}
    shares = frame["released_share_known"].astype(float)
    y_min = max(0.5, math.floor((shares.min() - 0.02) * 10) / 10)
    y_max = min(1.0, math.ceil((shares.max() + 0.02) * 10) / 10)

    height = 520
    left = 96
    top = 132
    plot_width = 700
    plot_height = 280
    right = left + plot_width
    bottom = top + plot_height
    colors = {
        "NYC Criminal Courts": BLUE,
        "Non-NYC City and District Courts": TEAL,
    }

    parts = [_svg_start("Monthly pretrial release rates", height=height)]
    parts.append(_panel(height=height))
    parts.append(
        _title(
            "Monthly pretrial release rates",
            "Supplemental pretrial branch, aggregated by court type",
        )
    )
    parts.append(
        _text(
            left,
            100,
            (
                f"Main policy sample: {int(policy_summary['row_count']):,} cases. "
                "Vertical markers show May 2022 and June 2023."
            ),
            17,
            TEXT_MID,
        )
    )

    for tick in [0.6, 0.7, 0.8, 0.9]:
        if y_min <= tick <= y_max:
            y = _scale_value(tick, y_min, y_max, bottom, top)
            parts.append(_line(left, y, right, y, GRID, 1))
            parts.append(_text(48, y + 4, f"{tick:.1f}", 14, TEXT_MID))

    for month in [m for m in months if m.endswith("-01")]:
        x = _scale_value(float(month_index[month]), 0.0, float(len(months) - 1), left, right)
        parts.append(_line(x, top, x, bottom, GRID, 1))
        parts.append(_text(x - 14, bottom + 26, month[:4], 14, TEXT_MID))

    for marker_month, label in [("2022-05", "May 2022"), ("2023-06", "Jun 2023")]:
        if marker_month not in month_index:
            continue
        x = _scale_value(float(month_index[marker_month]), 0.0, float(len(months) - 1), left, right)
        parts.append(_line(x, top, x, bottom, RED, 2))
        parts.append(_text(x + 6, top + 16, label, 14, RED))

    for court_type, color in colors.items():
        subset = frame[frame["court_type"] == court_type].sort_values("year_month")
        points = []
        for row in subset.itertuples(index=False):
            x = _scale_value(
                float(month_index[row.year_month]),
                0.0,
                float(len(months) - 1),
                left,
                right,
            )
            y = _scale_value(float(row.released_share_known), y_min, y_max, bottom, top)
            points.append((x, y))
        parts.append(_polyline(points, color, 3))
        last_x, last_y = points[-1]
        parts.append(_circle(last_x, last_y, 3.5, color))
        label = court_type.replace(" Criminal Courts", "").replace(
            " City and District Courts",
            "",
        )
        parts.append(_text(last_x + 10, last_y + 4, label, 15, color, weight="700"))

    parts.append(_line(left, bottom, right, bottom, TEXT_MID, 1.5))
    parts.append(_line(left, top, left, bottom, TEXT_MID, 1.5))
    parts.append(
        _footnote(
            (
                "Higher values mean a larger share of known release decisions "
                "ended with release rather than detention."
            ),
            y=492,
        )
    )
    parts.append(_svg_end())
    return "".join(parts)


def _svg_start(title: str, height: int = PLOT_HEIGHT) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PLOT_WIDTH}" height="{height}" '
        f'viewBox="0 0 {PLOT_WIDTH} {height}" role="img" aria-label="{_escape(title)}">'
    )


def _svg_end() -> str:
    return "</svg>"


def _panel(height: int = PLOT_HEIGHT) -> str:
    return (
        f'<rect x="0" y="0" width="{PLOT_WIDTH}" height="{height}" fill="{PLOT_BG}"/>'
        f'<rect x="18" y="18" width="{PLOT_WIDTH - 36}" height="{height - 36}" rx="20" '
        f'fill="{PLOT_PANEL}" stroke="{GRID}" stroke-width="1.5"/>'
    )


def _title(title: str, subtitle: str) -> str:
    return (
        _text(42, 48, title, 30, TEXT_DARK, weight="700")
        + _text(42, 74, subtitle, 18, TEXT_MID)
    )


def _footnote(text: str, y: float | None = None) -> str:
    return _text(42, y if y is not None else PLOT_HEIGHT - 28, text, 16, TEXT_MID)


def _rect(x: float, y: float, width: float, height: float, fill: str) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(width, 0):.1f}" '
        f'height="{height:.1f}" fill="{fill}"/>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str, stroke_width: float) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{stroke_width:.1f}"/>'
    )


def _polyline(points: list[tuple[float, float]], stroke: str, stroke_width: float) -> str:
    serialized = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (
        f'<polyline points="{serialized}" fill="none" stroke="{stroke}" '
        f'stroke-width="{stroke_width:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _circle(x: float, y: float, radius: float, fill: str) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}"/>'


def _text(
    x: float,
    y: float,
    text: str,
    size: int,
    fill: str,
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" '
        f'font-family="Georgia, serif" font-weight="{weight}">{_escape(text)}</text>'
    )


def _escape(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _scale_value(
    value: float,
    min_value: float,
    max_value: float,
    left: float,
    right: float,
) -> float:
    if math.isclose(min_value, max_value):
        return left
    return left + ((value - min_value) / (max_value - min_value)) * (right - left)


def _round_up_to_step(value: float, step: float) -> float:
    return math.ceil(value / step) * step


def _exposure_label(row: pd.Series) -> str:
    label_map = {
        "2022_new_qualifying_firearm_charge": "2022 new firearm",
        "2022_repeat_harm_or_theft_proxy": "2022 repeat harm/theft",
        "2022_second_firearm_offense_charge": "2022 second firearm",
        "2023_repeat_offender_proxy": "2023 repeat-offender proxy",
    }
    return label_map.get(str(row["exposure_group"]), str(row["exposure_group"]))
