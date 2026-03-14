from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.utils.io import read_json, write_json


@dataclass
class ManifestFile:
    year: int
    filename: str
    source_page_url: str
    resolved_url: str
    landed_via: str
    downloaded_at: str
    sha256: str
    bytes: int
    content_type: str
    manual_required: bool
    error: str | None = None


@dataclass
class Manifest:
    dataset: str = "oca_stat"
    snapshot_date: str = field(default_factory=lambda: date.today().isoformat())
    files: list[ManifestFile] = field(default_factory=list)

    def upsert(self, entry: ManifestFile) -> None:
        for index, existing in enumerate(self.files):
            if existing.year == entry.year:
                self.files[index] = entry
                break
        else:
            self.files.append(entry)
        self.files.sort(key=lambda item: item.year)


def get_manifest_path(path: Path | None = None) -> Path:
    return path or ensure_project_layout().raw_oca_stat / "manifest.json"


def load_manifest(path: Path | None = None) -> Manifest:
    manifest_path = get_manifest_path(path)
    if not manifest_path.exists():
        return Manifest()
    payload = read_json(manifest_path)
    return Manifest(
        dataset=payload["dataset"],
        snapshot_date=payload["snapshot_date"],
        files=[ManifestFile(**file_payload) for file_payload in payload.get("files", [])],
    )


def save_manifest(manifest: Manifest, path: Path | None = None) -> Path:
    manifest_path = get_manifest_path(path)
    write_json(
        manifest_path,
        {
            "dataset": manifest.dataset,
            "snapshot_date": manifest.snapshot_date,
            "files": [asdict(file_entry) for file_entry in manifest.files],
        },
    )
    return manifest_path
