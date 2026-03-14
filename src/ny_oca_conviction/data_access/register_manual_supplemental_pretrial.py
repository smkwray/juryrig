from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.data_access.supplemental_pretrial_common import (
    ARTIFACT_SPECS,
    SOURCE_PAGE_URL,
    artifact_spec,
    extract_csvs,
)
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import (
    SupplementalArtifact,
    load_manifest,
    save_manifest,
)
from ny_oca_conviction.utils.hashing import sha256_file


def _build_artifact(path: Path, role: str, landed_via: str) -> SupplementalArtifact:
    spec = artifact_spec("data_zip") if role.startswith("data_csv_part_") else artifact_spec(role)
    resolved_url = (
        artifact_spec("data_zip").resolved_url
        if role.startswith("data_csv_part_")
        else spec.resolved_url
    )
    content_type = "text/csv" if role.startswith("data_csv_part_") else spec.content_type
    return SupplementalArtifact(
        role=role,
        filename=path.name,
        source_page_url=SOURCE_PAGE_URL,
        resolved_url=resolved_url,
        landed_via=landed_via,
        downloaded_at=datetime.now(UTC).isoformat(),
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        content_type=content_type,
        manual_required=False,
    )


def register_manual_supplemental_pretrial(
    directory: Path,
) -> tuple[Path, list[SupplementalArtifact]]:
    paths = ensure_project_layout()
    manifest = load_manifest()
    manifest.remove_role("data_csv")
    manifest.remove_by_prefix("data_csv_part_")
    updated: list[SupplementalArtifact] = []

    existing = {path.name: path for path in directory.iterdir() if path.is_file()}
    for spec in ARTIFACT_SPECS:
        path = existing.get(spec.filename)
        if path is None:
            continue
        artifact = _build_artifact(path, spec.role, landed_via="manual")
        manifest.upsert(artifact)
        updated.append(artifact)

    zip_path = existing.get("Supplemental_Pretrial_Release_Data_File.zip")
    csv_paths = sorted(path for path in existing.values() if path.suffix.lower() == ".csv")
    if zip_path:
        extracted_paths = extract_csvs(zip_path, directory)
        existing.update({path.name: path for path in extracted_paths})
        csv_paths = sorted(path for path in existing.values() if path.suffix.lower() == ".csv")
    for index, csv_path in enumerate(csv_paths, start=1):
        csv_artifact = _build_artifact(
            csv_path,
            f"data_csv_part_{index}",
            landed_via="manual_extract" if zip_path else "manual",
        )
        manifest.upsert(csv_artifact)
        updated.append(csv_artifact)

    save_manifest(manifest)
    return paths.raw_supplemental_pretrial / "manifest.json", updated
