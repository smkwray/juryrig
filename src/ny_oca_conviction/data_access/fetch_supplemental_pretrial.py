from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.data_access.discover import USER_AGENT
from ny_oca_conviction.data_access.supplemental_pretrial_common import (
    ARTIFACT_SPECS,
    SOURCE_PAGE_URL,
    extract_csvs,
)
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import (
    SupplementalArtifact,
    load_manifest,
    save_manifest,
)
from ny_oca_conviction.utils.hashing import sha256_file


def fetch_supplemental_pretrial() -> tuple[Path, list[SupplementalArtifact]]:
    paths = ensure_project_layout()
    manifest = load_manifest()
    manifest.remove_role("data_csv")
    manifest.remove_by_prefix("data_csv_part_")
    landed: list[SupplementalArtifact] = []

    for spec in ARTIFACT_SPECS:
        output_path = paths.raw_supplemental_pretrial / spec.filename
        downloaded_at = datetime.now(UTC).isoformat()
        request = Request(spec.resolved_url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=120) as response:  # noqa: S310
            output_path.write_bytes(response.read())
            artifact = SupplementalArtifact(
                role=spec.role,
                filename=output_path.name,
                source_page_url=SOURCE_PAGE_URL,
                resolved_url=spec.resolved_url,
                landed_via="download",
                downloaded_at=downloaded_at,
                sha256=sha256_file(output_path),
                bytes=output_path.stat().st_size,
                content_type=response.headers.get_content_type(),
                manual_required=False,
            )
        manifest.upsert(artifact)
        landed.append(artifact)

    data_zip = manifest.get("data_zip")
    if data_zip:
        csv_paths = extract_csvs(
            paths.raw_supplemental_pretrial / data_zip.filename,
            paths.raw_supplemental_pretrial,
        )
        for index, csv_path in enumerate(csv_paths, start=1):
            csv_artifact = SupplementalArtifact(
                role=f"data_csv_part_{index}",
                filename=csv_path.name,
                source_page_url=SOURCE_PAGE_URL,
                resolved_url=data_zip.resolved_url,
                landed_via="download_extract",
                downloaded_at=datetime.now(UTC).isoformat(),
                sha256=sha256_file(csv_path),
                bytes=csv_path.stat().st_size,
                content_type="text/csv",
                manual_required=False,
            )
            manifest.upsert(csv_artifact)
            landed.append(csv_artifact)

    save_manifest(manifest)
    return paths.raw_supplemental_pretrial / "manifest.json", landed
