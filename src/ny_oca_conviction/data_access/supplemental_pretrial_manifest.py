from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.utils.io import read_json, write_json


@dataclass
class SupplementalArtifact:
    role: str
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
class SupplementalPretrialManifest:
    dataset: str = "supplemental_pretrial_release"
    snapshot_date: str = field(default_factory=lambda: date.today().isoformat())
    release_label: str = "2025-10"
    files: list[SupplementalArtifact] = field(default_factory=list)

    def upsert(self, artifact: SupplementalArtifact) -> None:
        for index, existing in enumerate(self.files):
            if existing.role == artifact.role:
                self.files[index] = artifact
                break
        else:
            self.files.append(artifact)
        self.files.sort(key=lambda item: item.role)

    def get(self, role: str) -> SupplementalArtifact | None:
        for artifact in self.files:
            if artifact.role == role:
                return artifact
        return None

    def find_by_prefix(self, prefix: str) -> list[SupplementalArtifact]:
        return sorted(
            [artifact for artifact in self.files if artifact.role.startswith(prefix)],
            key=lambda artifact: artifact.role,
        )

    def remove_by_prefix(self, prefix: str) -> None:
        self.files = [artifact for artifact in self.files if not artifact.role.startswith(prefix)]

    def remove_role(self, role: str) -> None:
        self.files = [artifact for artifact in self.files if artifact.role != role]


def get_manifest_path(path: Path | None = None) -> Path:
    return path or ensure_project_layout().raw_supplemental_pretrial / "manifest.json"


def load_manifest(path: Path | None = None) -> SupplementalPretrialManifest:
    manifest_path = get_manifest_path(path)
    if not manifest_path.exists():
        return SupplementalPretrialManifest()
    payload = read_json(manifest_path)
    return SupplementalPretrialManifest(
        dataset=payload["dataset"],
        snapshot_date=payload["snapshot_date"],
        release_label=payload.get("release_label", "2025-10"),
        files=[SupplementalArtifact(**file_payload) for file_payload in payload.get("files", [])],
    )


def save_manifest(
    manifest: SupplementalPretrialManifest,
    path: Path | None = None,
) -> Path:
    manifest_path = get_manifest_path(path)
    write_json(
        manifest_path,
        {
            "dataset": manifest.dataset,
            "snapshot_date": manifest.snapshot_date,
            "release_label": manifest.release_label,
            "files": [asdict(file_entry) for file_entry in manifest.files],
        },
    )
    return manifest_path
