from ny_oca_conviction.contracts.oca_stat_columns import (
    CANONICAL_COLUMNS,
    FORCE_CATEGORICAL,
    LEAKAGE_DENYLIST,
    PROTECTED_ATTRIBUTES,
    default_training_columns,
    missing_columns,
    normalize_columns,
)
from ny_oca_conviction.contracts.supplemental_pretrial_columns import (
    CANONICAL_COLUMNS as SUPPLEMENTAL_PRETRIAL_COLUMNS,
)


def test_contract_has_expected_column_count():
    assert len(CANONICAL_COLUMNS) == 28


def test_normalize_columns_handles_aliases():
    assert normalize_columns(["Row", "Article Section"]) == ["Row #", "Article.Section"]


def test_missing_columns_is_empty_for_canonical_contract():
    assert missing_columns(CANONICAL_COLUMNS) == []


def test_default_policies_include_leakage_and_protected_fields():
    assert "Disposition Type" in LEAKAGE_DENYLIST
    assert {"Gender", "Ethnicity", "Race"} == PROTECTED_ATTRIBUTES


def test_default_training_columns_can_include_protected_attributes():
    columns = default_training_columns(
        CANONICAL_COLUMNS,
        include_protected_attributes=True,
    )
    assert "Gender" in columns
    assert "Ethnicity" in columns
    assert "Race" in columns


def test_force_categorical_contains_expected_columns():
    assert "Law" in FORCE_CATEGORICAL
    assert "Article.Section" in FORCE_CATEGORICAL


def test_supplemental_pretrial_contract_has_expected_column_count():
    assert len(SUPPLEMENTAL_PRETRIAL_COLUMNS) == 114
