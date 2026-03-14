from __future__ import annotations

from dataclasses import dataclass
from math import exp
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.utils.io import write_json, write_markdown

LABEL_COLUMN = "conviction_label"
RACE_REFERENCE = "White"
CORE_CONTROL_COLUMNS = [
    "County",
    "Court Type",
    "Arrest Type",
    "Severity",
    "age_bucket",
    "Ethnicity",
    "Gender",
    "Arraign Year",
    "Arraign Month",
]
CHARGE_DETAIL_CONTROL_COLUMNS = CORE_CONTROL_COLUMNS + ["Weight", "Law", "Attempt Flag"]
MATCHED_STRATA_COLUMNS = CORE_CONTROL_COLUMNS + ["Weight"]


@dataclass(frozen=True)
class AdjustedSpecification:
    name: str
    controls: list[str]
    max_iter: int = 300
    c_value: float = 1.0


def analyze_race_association() -> dict[str, Any]:
    paths = ensure_project_layout()
    frame = _load_analysis_frame(paths.processed / "model_table.parquet")
    race_values = _race_categories(frame["Race"])

    raw_rates = _raw_rate_table(frame)
    specs = [
        AdjustedSpecification(name="core_adjusted", controls=CORE_CONTROL_COLUMNS),
        AdjustedSpecification(
            name="charge_detail_adjusted",
            controls=CHARGE_DETAIL_CONTROL_COLUMNS,
        ),
    ]

    adjusted_results: dict[str, Any] = {}
    for spec in specs:
        adjusted_results[spec.name] = _run_adjusted_spec(
            frame=frame,
            race_values=race_values,
            spec=spec,
        )

    matched = _compute_matched_strata_differences(
        frame=frame,
        race_values=race_values,
        strata_columns=MATCHED_STRATA_COLUMNS,
        reference_race=RACE_REFERENCE,
    )

    payload = {
        "row_count": int(len(frame)),
        "reference_race": RACE_REFERENCE,
        "raw_rates": raw_rates.to_dict(orient="records"),
        "adjusted_models": adjusted_results,
        "matched_strata": {
            "strata_columns": MATCHED_STRATA_COLUMNS,
            "comparisons": matched.to_dict(orient="records"),
        },
    }

    json_path = paths.validation_artifacts / "race_adjusted_association.json"
    markdown_path = paths.validation_artifacts / "race_adjusted_association.md"
    write_json(json_path, payload)
    write_markdown(markdown_path, _render_markdown_report(payload))
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(markdown_path)
    return payload


def _load_analysis_frame(path: Path) -> pd.DataFrame:
    columns = sorted(
        {
            LABEL_COLUMN,
            "Race",
            *CORE_CONTROL_COLUMNS,
            *CHARGE_DETAIL_CONTROL_COLUMNS,
            *MATCHED_STRATA_COLUMNS,
        }
    )
    frame = pd.read_parquet(path, columns=columns).copy()
    for column in columns:
        if column == LABEL_COLUMN:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
        else:
            frame[column] = frame[column].astype("string").fillna("unknown")
    return frame


def _race_categories(series: pd.Series) -> list[str]:
    observed = sorted(str(value) for value in series.astype("string").dropna().unique())
    ordered = [RACE_REFERENCE] if RACE_REFERENCE in observed else []
    ordered.extend(value for value in observed if value != RACE_REFERENCE)
    return ordered


def _build_pipeline(
    frame: pd.DataFrame,
    features: list[str],
    race_values: list[str],
    max_iter: int,
    c_value: float,
) -> Pipeline:
    categories: list[list[str]] = []
    for column in features:
        observed = sorted(str(value) for value in frame[column].astype("string").unique())
        if column == "Race":
            categories.append(race_values)
        else:
            categories.append(observed)

    encoder = OneHotEncoder(
        categories=categories,
        drop="first",
        handle_unknown="ignore",
        sparse_output=True,
    )
    preprocessor = ColumnTransformer([("cat", encoder, features)])
    model = LogisticRegression(
        max_iter=max_iter,
        solver="saga",
        C=c_value,
        random_state=7,
    )
    return Pipeline([("pre", preprocessor), ("model", model)])


def _run_adjusted_spec(
    frame: pd.DataFrame,
    race_values: list[str],
    spec: AdjustedSpecification,
) -> dict[str, Any]:
    features = spec.controls + ["Race"]
    pipeline = _build_pipeline(
        frame=frame,
        features=features,
        race_values=race_values,
        max_iter=spec.max_iter,
        c_value=spec.c_value,
    )
    pipeline.fit(frame[features], frame[LABEL_COLUMN])

    coefficient_frame = _coefficient_table(
        pipeline=pipeline,
        race_values=race_values,
    )
    standardized_frame = _standardized_probability_table(
        pipeline=pipeline,
        frame=frame,
        features=features,
        race_values=race_values,
        reference_race=RACE_REFERENCE,
    )
    return {
        "controls": spec.controls,
        "coefficient_table": coefficient_frame.to_dict(orient="records"),
        "standardized_probability_table": standardized_frame.to_dict(orient="records"),
    }


def _coefficient_table(pipeline: Pipeline, race_values: list[str]) -> pd.DataFrame:
    feature_names = pipeline.named_steps["pre"].get_feature_names_out()
    coefficients = pd.Series(pipeline.named_steps["model"].coef_[0], index=feature_names)
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "race": RACE_REFERENCE,
            "reference_race": True,
            "log_odds_vs_white": 0.0,
            "odds_ratio_vs_white": 1.0,
        }
    )
    for race in race_values:
        if race == RACE_REFERENCE:
            continue
        feature_name = f"cat__Race_{race}"
        coefficient = float(coefficients.get(feature_name, 0.0))
        rows.append(
            {
                "race": race,
                "reference_race": False,
                "log_odds_vs_white": coefficient,
                "odds_ratio_vs_white": exp(coefficient),
            }
        )
    return pd.DataFrame(rows)


def _standardized_probability_table(
    pipeline: Pipeline,
    frame: pd.DataFrame,
    features: list[str],
    race_values: list[str],
    reference_race: str,
    chunk_size: int = 250_000,
) -> pd.DataFrame:
    feature_frame = frame[features].copy()
    rows: list[dict[str, Any]] = []
    reference_mean: float | None = None
    for race in race_values:
        probability_sum = 0.0
        row_count = 0
        for start in range(0, len(feature_frame), chunk_size):
            stop = min(start + chunk_size, len(feature_frame))
            chunk = feature_frame.iloc[start:stop].copy()
            chunk["Race"] = race
            probability_sum += float(pipeline.predict_proba(chunk)[:, 1].sum())
            row_count += len(chunk)
        mean_probability = probability_sum / row_count
        if race == reference_race:
            reference_mean = mean_probability
        rows.append(
            {
                "race": race,
                "mean_predicted_probability": mean_probability,
            }
        )

    if reference_mean is None:
        raise ValueError(f"Reference race {reference_race!r} is missing from the analysis.")

    output = pd.DataFrame(rows)
    output["diff_vs_white_pp"] = (
        (output["mean_predicted_probability"] - reference_mean) * 100.0
    )
    return output


def _compute_matched_strata_differences(
    frame: pd.DataFrame,
    race_values: list[str],
    strata_columns: list[str],
    reference_race: str,
) -> pd.DataFrame:
    grouped = (
        frame.groupby(strata_columns + ["Race"], observed=False)[LABEL_COLUMN]
        .agg(["mean", "size"])
        .reset_index()
    )
    reference = grouped[grouped["Race"] == reference_race].rename(
        columns={"mean": "reference_rate", "size": "reference_n"}
    )
    rows: list[dict[str, Any]] = []
    reference_total = int((frame["Race"] == reference_race).sum())
    for race in race_values:
        if race == reference_race:
            continue
        other = grouped[grouped["Race"] == race].rename(
            columns={"mean": "comparison_rate", "size": "comparison_n"}
        )
        merged = reference.merge(other, on=strata_columns, how="inner")
        total_comparison = int((frame["Race"] == race).sum())
        if merged.empty:
            rows.append(
                {
                    "race": race,
                    "weighted_diff_vs_white_pp": np.nan,
                    "shared_strata_count": 0,
                    "shared_reference_rows": 0,
                    "shared_comparison_rows": 0,
                    "shared_reference_share": 0.0,
                    "shared_comparison_share": 0.0,
                }
            )
            continue
        weights = merged["reference_n"] + merged["comparison_n"]
        diff = np.average(
            merged["comparison_rate"] - merged["reference_rate"],
            weights=weights,
        )
        shared_reference_rows = int(merged["reference_n"].sum())
        shared_comparison_rows = int(merged["comparison_n"].sum())
        rows.append(
            {
                "race": race,
                "weighted_diff_vs_white_pp": diff * 100.0,
                "shared_strata_count": int(len(merged)),
                "shared_reference_rows": shared_reference_rows,
                "shared_comparison_rows": shared_comparison_rows,
                "shared_reference_share": shared_reference_rows / reference_total,
                "shared_comparison_share": shared_comparison_rows / total_comparison,
            }
        )
    return pd.DataFrame(rows)


def _raw_rate_table(frame: pd.DataFrame) -> pd.DataFrame:
    output = (
        frame.groupby("Race", observed=False)[LABEL_COLUMN]
        .agg(["mean", "size"])
        .reset_index()
        .rename(columns={"Race": "race", "mean": "conviction_rate", "size": "row_count"})
        .sort_values("race")
        .reset_index(drop=True)
    )
    output["conviction_rate"] = output["conviction_rate"].astype(float)
    output["row_count"] = output["row_count"].astype(int)
    return output


def _render_markdown_report(payload: dict[str, Any]) -> str:
    raw_rates = pd.DataFrame(payload["raw_rates"])
    core = pd.DataFrame(
        payload["adjusted_models"]["core_adjusted"]["standardized_probability_table"]
    )
    detail = pd.DataFrame(
        payload["adjusted_models"]["charge_detail_adjusted"]["standardized_probability_table"]
    )
    matched = pd.DataFrame(payload["matched_strata"]["comparisons"])

    lines = [
        "# Race-Adjusted Association Summary",
        "",
        f"- row_count: {payload['row_count']}",
        f"- reference_race: {payload['reference_race']}",
        "",
        "## Raw conviction rates by race",
        *_markdown_table(raw_rates),
        "",
        "## Core adjusted model",
        (
            "Controls: County, Court Type, Arrest Type, Severity, age_bucket, "
            "Ethnicity, Gender, Arraign Year, Arraign Month."
        ),
        "",
        "### Standardized predicted probability by race",
        *_markdown_table(core),
        "",
        "## Charge-detail adjusted model",
        "Controls: core controls plus Weight, Law, Attempt Flag.",
        "",
        "### Standardized predicted probability by race",
        *_markdown_table(detail),
        "",
        "## Matched-strata comparison",
        (
            "Strata: County, Court Type, Arrest Type, Severity, Weight, "
            "age_bucket, Ethnicity, Gender, Arraign Year, Arraign Month."
        ),
        "",
        *_markdown_table(matched),
    ]
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame) -> list[str]:
    if frame.empty:
        return ["No rows."]
    header = "| " + " | ".join(frame.columns.astype(str)) + " |"
    separator = "|" + "|".join([" --- "] * len(frame.columns)) + "|"
    rows = [header, separator]
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(value) for value in row.tolist()) + " |")
    return rows
