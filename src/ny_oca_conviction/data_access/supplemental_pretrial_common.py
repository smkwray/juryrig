from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

SOURCE_PAGE_URL = "https://www.criminaljustice.ny.gov/crimnet/ojsa/stats.htm"


@dataclass(frozen=True)
class ArtifactSpec:
    role: str
    filename: str
    resolved_url: str
    content_type: str


ARTIFACT_SPECS = [
    ArtifactSpec(
        role="data_zip",
        filename="Supplemental_Pretrial_Release_Data_File.zip",
        resolved_url=(
            "https://www.criminaljustice.ny.gov/crimnet/ojsa/pretrial-release/"
            "Supplemental_Pretrial_Release_Data_File.zip"
        ),
        content_type="application/zip",
    ),
    ArtifactSpec(
        role="source_notes",
        filename="Supplemental_Pretrial_Release_Data_File_Source_Notes.pdf",
        resolved_url=(
            "https://www.criminaljustice.ny.gov/crimnet/ojsa/pretrial-release/"
            "Supplemental_Pretrial_Release_Data_File_Source_Notes.pdf"
        ),
        content_type="application/pdf",
    ),
    ArtifactSpec(
        role="data_dictionary",
        filename="Supplemental_Pretrial_Release_Data_Dictionary.xlsx",
        resolved_url=(
            "https://www.criminaljustice.ny.gov/crimnet/ojsa/pretrial-release/"
            "Supplemental_Pretrial_Release_Data_Dictionary.xlsx"
        ),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    ),
    ArtifactSpec(
        role="summary_tables",
        filename="Supplemental_Pretrial_Release_Summary_Tables.pdf",
        resolved_url=(
            "https://www.criminaljustice.ny.gov/crimnet/ojsa/pretrial-release/"
            "Supplemental_Pretrial_Release_Summary_Tables.pdf"
        ),
        content_type="application/pdf",
    ),
]


def artifact_spec(role: str) -> ArtifactSpec:
    for spec in ARTIFACT_SPECS:
        if spec.role == role:
            return spec
    raise KeyError(f"Unknown supplemental pretrial artifact role: {role}")


def extract_csvs(zip_path: Path, output_dir: Path) -> list[Path]:
    with ZipFile(zip_path) as archive:
        csv_names = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
        if not csv_names:
            raise FileNotFoundError(f"No CSV file found in archive: {zip_path.name}")
        extracted_paths: list[Path] = []
        for csv_name in csv_names:
            target_path = output_dir / Path(csv_name).name
            with archive.open(csv_name) as source, target_path.open("wb") as handle:
                while chunk := source.read(1024 * 1024):
                    handle.write(chunk)
            extracted_paths.append(target_path)
    return extracted_paths
