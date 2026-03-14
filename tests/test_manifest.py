from pathlib import Path

from ny_oca_conviction.data_access.manifest import (
    Manifest,
    ManifestFile,
    load_manifest,
    save_manifest,
)


def test_manifest_round_trip(tmp_path: Path):
    manifest = Manifest(
        files=[
            ManifestFile(
                year=2025,
                filename="OCA-STAT-Act-2025.csv",
                source_page_url="https://example.test",
                resolved_url="https://example.test/file.csv",
                landed_via="manual",
                downloaded_at="2026-03-07T00:00:00+00:00",
                sha256="abc",
                bytes=12,
                content_type="text/csv",
                manual_required=False,
            )
        ]
    )
    output = tmp_path / "manifest.json"
    save_manifest(manifest, output)
    loaded = load_manifest(output)
    assert loaded.dataset == "oca_stat"
    assert loaded.files[0].filename == "OCA-STAT-Act-2025.csv"
