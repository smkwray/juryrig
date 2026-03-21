from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.data_access.discover import (
    DiscoveryUnavailableError,
    discover_sources,
    save_discovery,
)
from ny_oca_conviction.data_access.fetch import fetch_oca_stat
from ny_oca_conviction.data_access.fetch_supplemental_pretrial import fetch_supplemental_pretrial
from ny_oca_conviction.data_access.manifest import load_manifest
from ny_oca_conviction.data_access.register_manual import register_manual_oca_stat
from ny_oca_conviction.data_access.register_manual_supplemental_pretrial import (
    register_manual_supplemental_pretrial,
)
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import (
    load_manifest as load_supplemental_pretrial_manifest,
)
from ny_oca_conviction.data_access.validate_raw import validate_raw_files
from ny_oca_conviction.data_access.validate_supplemental_pretrial import (
    validate_supplemental_pretrial_files,
)
from ny_oca_conviction.dataset.build import build_dataset
from ny_oca_conviction.dataset.policy_effects_supplemental_pretrial import (
    build_supplemental_pretrial_policy_effects,
)
from ny_oca_conviction.dataset.policy_sample_supplemental_pretrial import (
    build_supplemental_pretrial_policy_sample,
)
from ny_oca_conviction.dataset.policy_tables_supplemental_pretrial import (
    build_supplemental_pretrial_policy_tables,
)
from ny_oca_conviction.dataset.replicate_supplemental_pretrial import (
    replicate_supplemental_pretrial_tables,
)
from ny_oca_conviction.dataset.summarize_supplemental_pretrial import (
    summarize_supplemental_pretrial,
)
from ny_oca_conviction.evaluation.race_association import analyze_race_association
from ny_oca_conviction.evaluation.report import evaluate_run
from ny_oca_conviction.models.train import train_models
from ny_oca_conviction.reports.figures import build_public_figures
from ny_oca_conviction.utils.io import read_json

app = typer.Typer(no_args_is_help=True)
console = Console()


def _render_sources(records) -> None:
    table = Table(title="Discovered OCA-STAT sources")
    table.add_column("Year")
    table.add_column("Link text")
    table.add_column("Resolved URL")
    for record in records:
        table.add_row(str(record.year), record.link_text, record.resolved_url)
    console.print(table)


@app.command("discover-sources")
def discover_sources_command() -> None:
    ensure_project_layout()
    try:
        records = discover_sources()
    except DiscoveryUnavailableError as exc:
        console.print(f"Discovery blocked: {exc}")
        console.print(
            "Use a normal browser to download the yearly CSVs, then run "
            "`register-manual-oca-stat --path data/raw/oca_stat`."
        )
        raise typer.Exit(code=1) from exc
    output_path = save_discovery(records)
    _render_sources(records)
    console.print(f"Saved discovery output to {output_path}")


@app.command("fetch-oca-stat")
def fetch_oca_stat_command(
    years: Annotated[
        str,
        typer.Option(help="all,current, or comma-separated years"),
    ] = "all",
) -> None:
    requested_years = None
    if years not in {"all", "current"}:
        requested_years = [int(item.strip()) for item in years.split(",") if item.strip()]
    manifest_path, entries = fetch_oca_stat(requested_years)
    console.print(f"Updated manifest at {manifest_path}")
    for entry in entries:
        status = "manual_required" if entry.manual_required else "downloaded"
        console.print(f"- {entry.year}: {status}")


@app.command("register-manual-oca-stat")
def register_manual_oca_stat_command(
    path: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False),
    ],
) -> None:
    manifest_path, entries = register_manual_oca_stat(path)
    console.print(f"Updated manifest at {manifest_path}")
    console.print(f"Registered {len(entries)} local files.")


@app.command("show-manifest")
def show_manifest_command() -> None:
    manifest = load_manifest()
    payload = {
        "dataset": manifest.dataset,
        "snapshot_date": manifest.snapshot_date,
        "files": [entry.__dict__ for entry in manifest.files],
    }
    console.print_json(data=payload)


@app.command("fetch-supplemental-pretrial")
def fetch_supplemental_pretrial_command() -> None:
    manifest_path, entries = fetch_supplemental_pretrial()
    console.print(f"Updated manifest at {manifest_path}")
    for entry in entries:
        console.print(f"- {entry.role}: {entry.filename}")


@app.command("register-manual-supplemental-pretrial")
def register_manual_supplemental_pretrial_command(
    path: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False),
    ],
) -> None:
    manifest_path, entries = register_manual_supplemental_pretrial(path)
    console.print(f"Updated manifest at {manifest_path}")
    console.print(f"Registered {len(entries)} supplemental pretrial artifacts.")


@app.command("show-supplemental-pretrial-manifest")
def show_supplemental_pretrial_manifest_command() -> None:
    manifest = load_supplemental_pretrial_manifest()
    payload = {
        "dataset": manifest.dataset,
        "snapshot_date": manifest.snapshot_date,
        "release_label": manifest.release_label,
        "files": [entry.__dict__ for entry in manifest.files],
    }
    console.print_json(data=payload)


@app.command("validate-raw")
def validate_raw_command() -> None:
    results, report_path = validate_raw_files()
    for result in results:
        console.print(f"{result.year}: {'ok' if result.ok else 'fail'}")
    console.print(f"Schema report written to {report_path}")


@app.command("validate-supplemental-pretrial")
def validate_supplemental_pretrial_command() -> None:
    results, report_path = validate_supplemental_pretrial_files()
    for result in results:
        status = "ok" if result.ok else "fail"
        console.print(f"{result.role} ({result.filename or 'none'}): {status}")
    console.print(f"Schema report written to {report_path}")


@app.command("build-dataset")
def build_dataset_command(
    snapshot_date: Annotated[str, typer.Option()],
    config: Annotated[Path, typer.Option()] = Path("configs/dataset.yaml"),
) -> None:
    payload = build_dataset(snapshot_date=snapshot_date, config_path=config)
    console.print_json(data=payload)


@app.command("train")
def train_command(
    config: Annotated[Path, typer.Option()] = Path("configs/train_baseline.yaml"),
) -> None:
    payload = train_models(config)
    console.print_json(data=payload)


@app.command("evaluate")
def evaluate_command(
    run_id: Annotated[str, typer.Option()] = "latest",
    subgroup_columns: Annotated[str, typer.Option()] = "Race,Ethnicity,Gender,age_bucket,Region",
) -> None:
    columns = [column.strip() for column in subgroup_columns.split(",") if column.strip()]
    payload = evaluate_run(run_id, columns)
    console.print_json(data=payload)


@app.command("report")
def report_command(run_id: Annotated[str, typer.Option()] = "latest") -> None:
    run_dir = ensure_project_layout().runs / run_id if run_id != "latest" else None
    if run_id == "latest":
        payload = evaluate_run("latest", ["Race", "Ethnicity", "Gender", "age_bucket", "Region"])
    else:
        report_path = (run_dir or Path()).joinpath("report.md")
        payload = {"report": str(report_path)}
        if not report_path.exists():
            payload = evaluate_run(run_id, ["Race", "Ethnicity", "Gender", "age_bucket", "Region"])
    console.print_json(data=payload)


@app.command("summarize-cohorts")
def summarize_cohorts_command() -> None:
    summary = read_json(ensure_project_layout().processed / "model_table_summary.json")
    console.print_json(data=summary)


@app.command("summarize-supplemental-pretrial")
def summarize_supplemental_pretrial_command() -> None:
    payload = summarize_supplemental_pretrial()
    console.print_json(data=payload)


@app.command("replicate-supplemental-pretrial")
def replicate_supplemental_pretrial_command() -> None:
    payload = replicate_supplemental_pretrial_tables()
    console.print_json(data=payload)


@app.command("build-supplemental-pretrial-policy-sample")
def build_supplemental_pretrial_policy_sample_command() -> None:
    payload = build_supplemental_pretrial_policy_sample()
    console.print_json(data=payload)


@app.command("build-supplemental-pretrial-policy-tables")
def build_supplemental_pretrial_policy_tables_command() -> None:
    payload = build_supplemental_pretrial_policy_tables()
    console.print_json(data=payload)


@app.command("build-supplemental-pretrial-policy-effects")
def build_supplemental_pretrial_policy_effects_command() -> None:
    payload = build_supplemental_pretrial_policy_effects()
    console.print_json(data=payload)


@app.command("build-public-figures")
def build_public_figures_command(
    run_id: Annotated[str, typer.Option()] = "latest",
) -> None:
    payload = build_public_figures(run_id=run_id)
    console.print_json(data=payload)


@app.command("analyze-race-association")
def analyze_race_association_command() -> None:
    payload = analyze_race_association()
    console.print_json(data=payload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
