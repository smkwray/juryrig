from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOURCE_PAGE_URL = "https://ww2.nycourts.gov/oca-stat-act-31371"


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    configs: Path
    data: Path
    raw_oca_stat: Path
    raw_supplemental_pretrial: Path
    processed: Path
    processed_supplemental_pretrial: Path
    reference: Path
    artifacts: Path
    validation_artifacts: Path
    runs: Path


def get_project_paths() -> ProjectPaths:
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        configs=root / "configs",
        data=root / "data",
        raw_oca_stat=root / "data" / "raw" / "oca_stat",
        processed=root / "data" / "processed",
        raw_supplemental_pretrial=root / "data" / "raw" / "supplemental_pretrial",
        processed_supplemental_pretrial=root / "data" / "processed" / "supplemental_pretrial",
        reference=root / "data" / "reference",
        artifacts=root / "artifacts",
        validation_artifacts=root / "artifacts" / "data_validation",
        runs=root / "artifacts" / "runs",
    )


def ensure_project_layout() -> ProjectPaths:
    paths = get_project_paths()
    for path in (
        paths.raw_oca_stat,
        paths.raw_supplemental_pretrial,
        paths.processed,
        paths.processed_supplemental_pretrial,
        paths.reference,
        paths.validation_artifacts,
        paths.runs,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths
