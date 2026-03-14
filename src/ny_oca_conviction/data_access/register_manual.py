from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.data_access.discover import (
    discover_sources,
    load_saved_discovery,
    save_discovery,
)
from ny_oca_conviction.data_access.manifest import ManifestFile, load_manifest, save_manifest
from ny_oca_conviction.utils.hashing import sha256_file

FILENAME_RE = re.compile(r"OCA-STAT-Act-(\d{4})\.csv$")


def register_manual_oca_stat(directory: Path) -> tuple[Path, list[ManifestFile]]:
    paths = ensure_project_layout()
    try:
        discovered = {record.year: record for record in discover_sources()}
        save_discovery(list(discovered.values()))
    except Exception:
        discovered = {record.year: record for record in load_saved_discovery()}
    manifest = load_manifest()
    updated: list[ManifestFile] = []
    for path in sorted(directory.glob("OCA-STAT-Act-*.csv")):
        match = FILENAME_RE.fullmatch(path.name)
        if not match:
            continue
        year = int(match.group(1))
        source = discovered.get(year)
        downloaded_at = datetime.now(UTC).isoformat()
        entry = ManifestFile(
            year=year,
            filename=path.name,
            source_page_url=source.source_page_url if source else "",
            resolved_url=source.resolved_url if source else "",
            landed_via="manual",
            downloaded_at=downloaded_at,
            sha256=sha256_file(path),
            bytes=path.stat().st_size,
            content_type="text/csv",
            manual_required=False,
        )
        manifest.upsert(entry)
        updated.append(entry)
    save_manifest(manifest)
    return paths.raw_oca_stat / "manifest.json", updated
