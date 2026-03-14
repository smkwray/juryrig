from __future__ import annotations

from pathlib import Path

import pandas as pd

from ny_oca_conviction.config import ensure_project_layout
from ny_oca_conviction.contracts.oca_stat_columns import CANONICAL_COLUMNS, normalize_columns
from ny_oca_conviction.data_access.manifest import load_manifest

CSV_ENCODINGS = ["utf-8-sig", "cp1252", "latin-1"]


def read_oca_stat_csv(path: Path) -> pd.DataFrame:
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


def load_raw_oca_stat() -> pd.DataFrame:
    paths = ensure_project_layout()
    manifest = load_manifest()
    frames: list[pd.DataFrame] = []
    for entry in manifest.files:
        path = paths.raw_oca_stat / entry.filename
        if not path.exists():
            continue
        frame = read_oca_stat_csv(path)
        frame["source_year"] = entry.year
        frame["source_filename"] = entry.filename
        frames.append(frame)
    if not frames:
        raise FileNotFoundError("No OCA-STAT CSV files are available under data/raw/oca_stat.")
    return pd.concat(frames, ignore_index=True)
