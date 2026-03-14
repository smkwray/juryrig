from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.data_access.discover import (
    USER_AGENT,
    DiscoveryUnavailableError,
    discover_sources,
    load_saved_discovery,
    save_discovery,
)
from ny_oca_conviction.data_access.manifest import ManifestFile, load_manifest, save_manifest
from ny_oca_conviction.utils.hashing import sha256_file


def _looks_like_csv(sample: bytes) -> bool:
    decoded = sample.decode("utf-8", errors="ignore").lstrip()
    return not decoded.startswith("<") and "," in decoded


def fetch_oca_stat(years: list[int] | None = None) -> tuple[Path, list[ManifestFile]]:
    paths = ensure_project_layout()
    try:
        discovered = discover_sources()
        save_discovery(discovered)
    except DiscoveryUnavailableError:
        discovered = load_saved_discovery()
        if not discovered:
            raise
    manifest = load_manifest()
    selected_years = {record.year for record in discovered} if years is None else set(years)
    landed: list[ManifestFile] = []

    for record in discovered:
        if record.year not in selected_years:
            continue
        filename = f"OCA-STAT-Act-{record.year}.csv"
        output_path = paths.raw_oca_stat / filename
        downloaded_at = datetime.now(UTC).isoformat()
        request = Request(record.resolved_url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=60) as response:  # noqa: S310
                sample = response.read(4096)
                if not _looks_like_csv(sample):
                    raise ValueError("response did not look like CSV")
                remainder = response.read()
                output_path.write_bytes(sample + remainder)
                entry = ManifestFile(
                    year=record.year,
                    filename=filename,
                    source_page_url=record.source_page_url,
                    resolved_url=record.resolved_url,
                    landed_via="download",
                    downloaded_at=downloaded_at,
                    sha256=sha256_file(output_path),
                    bytes=output_path.stat().st_size,
                    content_type=response.headers.get_content_type(),
                    manual_required=False,
                )
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            entry = ManifestFile(
                year=record.year,
                filename=filename,
                source_page_url=record.source_page_url,
                resolved_url=record.resolved_url,
                landed_via="download",
                downloaded_at=downloaded_at,
                sha256="",
                bytes=0,
                content_type="",
                manual_required=True,
                error=str(exc),
            )
        manifest.upsert(entry)
        landed.append(entry)

    save_manifest(manifest)
    return paths.raw_oca_stat / "manifest.json", landed
