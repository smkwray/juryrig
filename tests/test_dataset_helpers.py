from pathlib import Path

import pandas as pd
import pytest

from ny_oca_conviction.dataset.build import _string_key_counts
from ny_oca_conviction.dataset.features import resolve_feature_columns
from ny_oca_conviction.dataset.normalize import read_oca_stat_csv


def test_read_oca_stat_csv_falls_back_from_utf8(tmp_path: Path):
    csv_path = tmp_path / "oca.csv"
    csv_path.write_bytes(
        (
            "Row #,Court Type,Region,District,County,Court,Arresting Agency,Arrest Type,"
            "Arraign Year,Arraign Month,Top Charge at Arraignment,Severity,Weight,Law,"
            "Article.Section,Attempt Flag,Gender,Ethnicity,Race,Arrest Age,Docket Status,"
            "Disposition Type,Disposition Detail,Dismissal Reason,Most Severe Sentence,"
            "Fines Imposed,Fees Imposed,Surcharges Imposed\n"
            "1,Criminal,NYC,1,Kings,Crim Court,NYPD,Arrest,2024,1,Charge – A,M,1,PL,"
            "120.00,N,Male,Unknown,Unknown,25,Disposed,Plea,,,,0,0,0\n"
        ).encode("cp1252")
    )

    frame = read_oca_stat_csv(csv_path)
    assert len(frame) == 1
    assert frame.iloc[0]["Top Charge at Arraignment"] == "Charge – A"


def test_string_key_counts_normalizes_pandas_scalars():
    series = pd.Series([1, 1, 0, pd.NA], dtype="Int64")
    counts = _string_key_counts(series)
    assert counts == {"0": 1, "1": 2, "<NA>": 1}


def test_resolve_feature_columns_includes_protected_attributes_when_configured():
    frame = pd.DataFrame(
        {
            "Gender": ["Male"],
            "Ethnicity": ["Unknown"],
            "Race": ["Unknown"],
            "County": ["Kings"],
            "Arrest Age": [25],
            "convicted": [1],
        }
    )

    columns = resolve_feature_columns(frame, protected_attribute_mode="include_all")

    assert "Gender" in columns
    assert "Ethnicity" in columns
    assert "Race" in columns


def test_resolve_feature_columns_rejects_unknown_protected_attribute_mode():
    frame = pd.DataFrame({"County": ["Kings"]})

    with pytest.raises(ValueError, match="protected_attribute_mode"):
        resolve_feature_columns(frame, protected_attribute_mode="invalid")
