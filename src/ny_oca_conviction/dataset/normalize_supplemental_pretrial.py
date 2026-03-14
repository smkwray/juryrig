from __future__ import annotations

from pathlib import Path

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.contracts.supplemental_pretrial_columns import (
    CANONICAL_COLUMNS,
    normalize_columns,
)
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import load_manifest

CSV_ENCODINGS = ["utf-8-sig", "cp1252", "latin-1"]


def read_supplemental_pretrial_csv(path: Path) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None
    frame: pd.DataFrame | None = None
    for encoding in CSV_ENCODINGS:
        try:
            frame = pd.read_csv(
                path,
                dtype="string",
                keep_default_na=False,
                encoding=encoding,
            )
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    if frame is None:
        raise last_error or UnicodeDecodeError("utf-8", b"", 0, 1, "unable to decode CSV")
    frame.columns = normalize_columns(frame.columns)
    for column in CANONICAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[CANONICAL_COLUMNS].copy()


def load_raw_supplemental_pretrial() -> pd.DataFrame:
    paths = ensure_project_layout()
    manifest = load_manifest()
    data_csvs = manifest.find_by_prefix("data_csv_part_")
    if not data_csvs:
        raise FileNotFoundError(
            "No supplemental pretrial CSV is registered under data/raw/supplemental_pretrial."
        )
    frames: list[pd.DataFrame] = []
    for artifact in data_csvs:
        path = paths.raw_supplemental_pretrial / artifact.filename
        if not path.exists():
            raise FileNotFoundError(f"Registered supplemental pretrial CSV does not exist: {path}")
        frame = read_supplemental_pretrial_csv(path)
        frame["source_file"] = artifact.filename
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
