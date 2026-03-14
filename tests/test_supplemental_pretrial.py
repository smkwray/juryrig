from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from ny_oca_conviction.contracts.supplemental_pretrial_columns import CANONICAL_COLUMNS
from ny_oca_conviction.data_access.supplemental_pretrial_common import extract_csvs
from ny_oca_conviction.data_access.supplemental_pretrial_manifest import (
    SupplementalArtifact,
    SupplementalPretrialManifest,
    load_manifest,
    save_manifest,
)
from ny_oca_conviction.data_access.validate_supplemental_pretrial import _validate_csv
from ny_oca_conviction.dataset.policy_effects_supplemental_pretrial import (
    _policy_exposure_diffs,
    _policy_exposure_windows,
)
from ny_oca_conviction.dataset.policy_sample_supplemental_pretrial import (
    _charge_article,
    _charge_exposure_2022,
    _charge_exposure_2023,
    _charge_exposure_template,
    _charge_root,
    _charge_subdivision,
    _policy_sample,
    _row_exposure_2022,
    _row_exposure_2023,
)
from ny_oca_conviction.dataset.policy_tables_supplemental_pretrial import (
    _amendment_window_summary,
    _monthly_disposition_table,
    _monthly_release_table,
    _severity_bucket,
)
from ny_oca_conviction.dataset.replicate_supplemental_pretrial import (
    _compare_tables,
    _table1_annual,
    _table9_annual,
)


def test_supplemental_pretrial_manifest_round_trip(tmp_path: Path):
    manifest = SupplementalPretrialManifest(
        files=[
            SupplementalArtifact(
                role="data_csv_part_1",
                filename="PretrialRelease_2019_2024_Part_1.csv",
                source_page_url="https://example.test",
                resolved_url="https://example.test/file.zip",
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
    assert loaded.dataset == "supplemental_pretrial_release"
    assert loaded.files[0].role == "data_csv_part_1"


def test_extract_csvs_from_zip(tmp_path: Path):
    zip_path = tmp_path / "supplemental.zip"
    csv_names = ["PretrialRelease_2019_2024_Part_2.csv", "PretrialRelease_2019_2024_Part_1.csv"]
    with ZipFile(zip_path, "w") as archive:
        for csv_name in csv_names:
            archive.writestr(csv_name, "caseid,arr_age\n1,25\n")

    extracted = extract_csvs(zip_path, tmp_path)

    assert [path.name for path in extracted] == sorted(csv_names)
    assert extracted[0].read_text(encoding="utf-8") == "caseid,arr_age\n1,25\n"


def test_validate_supplemental_pretrial_csv_accepts_contract_columns(tmp_path: Path):
    csv_path = tmp_path / "Supplemental_Pretrial_Release_Data_File.csv"
    csv_path.write_text(",".join(CANONICAL_COLUMNS) + "\n", encoding="utf-8")

    result = _validate_csv(csv_path)

    assert result.ok
    assert result.column_count == len(CANONICAL_COLUMNS)


def test_table1_and_table9_helpers_roll_up_expected_counts():
    frame = pd.DataFrame(
        {
            "caseid": ["1", "2", "3", "4"],
            "court_type": [
                "NYC Criminal Courts",
                "NYC Criminal Courts",
                "Non-NYC Town and Village Justice Courts",
                "Non-NYC Town and Village Justice Courts",
            ],
            "year_label": ["2019", "2019", "2023(6M)", "2023(6M)"],
            "larg_rel_decision": ["ROR", "Disposed at arraign", "Unknown", "Remanded"],
            "disposition": ["Conviction", "Dismissed", "Pending", "Covered by/Consolidated"],
        }
    )

    table1 = _table1_annual(frame)
    table9 = _table9_annual(frame)

    nyc = table1[table1["court_type"] == "NYC Criminal Courts"].iloc[0]
    assert nyc["total_arraignments"] == 2
    assert nyc["release_decisions"] == 1
    assert nyc["disposed_at_arraignment"] == 1
    assert nyc["unknown_release_decisions"] == 0

    town = table9[table9["court_type"] == "Non-NYC Town and Village Justice Courts"].iloc[0]
    assert town["total_arraignments"] == 2
    assert town["conviction_or_yo"] == 0
    assert town["dismissed_or_other_favorable"] == 1
    assert town["pending"] == 1


def test_compare_tables_marks_matching_rows():
    computed = pd.DataFrame(
        {
            "court_type": ["NYC Criminal Courts"],
            "year_label": ["2019"],
            "total_arraignments": [10],
        }
    )
    official = pd.DataFrame(
        {
            "court_type": ["NYC Criminal Courts"],
            "year_label": ["2019"],
            "total_arraignments": [10],
        }
    )

    compared = _compare_tables(computed, official, ["total_arraignments"])

    assert bool(compared.loc[0, "total_arraignments_match"])
    assert bool(compared.loc[0, "all_metrics_match"])


def test_policy_sample_filters_to_main_window_and_adds_month_indexes():
    frame = pd.DataFrame(
        {
            "caseid": ["1", "2", "3"],
            "larg_court_type": [
                "NYC Criminal Court",
                "Non-NYC City or District Court",
                "Non-NYC Town or Village Justice Court",
            ],
            "larg_yr": ["2021", "2023", "2023"],
            "larg_mo": ["4", "6", "7"],
            "larg_rel_decision": ["ROR", "Bail Set", "ROR"],
            "disposition": ["Conviction", "Pending", "Dismissed"],
            "larg_charge": ["A", "B", "C"],
            "larg_class": ["A Misdemeanor", "D Felony", "A Misdemeanor"],
            "larg_attempt": ["Completed", "Completed", "Completed"],
            "larg_vfo": ["Not VFO", "VFO", "Not VFO"],
            "larg_firearm": ["Not Firearm Charge", "Top Charge is Firearm", "Not Firearm Charge"],
            "pend_vfo": ["No", "Yes", "No"],
            "pend_nonvfo": ["No", "No", "No"],
            "pend_misd": ["No", "No", "No"],
        }
    )

    sample = _policy_sample(frame)

    assert len(sample) == 2
    assert sample["court_type"].tolist() == [
        "NYC Criminal Courts",
        "Non-NYC City and District Courts",
    ]
    assert sample["month_index_2022_05"].tolist() == [-13, 13]
    assert sample["post_2023_amendment"].tolist() == [False, True]
    assert sample["row_exposure_2023"].tolist() == ["comparison", "comparison"]


def test_charge_exposure_template_rolls_up_year_counts():
    frame = pd.DataFrame(
        {
            "caseid": ["1", "2", "3"],
            "court_type": [
                "NYC Criminal Courts",
                "NYC Criminal Courts",
                "Non-NYC City and District Courts",
            ],
            "arraign_year": [2021, 2022, 2022],
            "larg_charge": ["PL 1", "PL 1", "PL 2"],
            "larg_class": ["A Misdemeanor", "A Misdemeanor", "D Felony"],
            "larg_attempt": ["Completed", "Completed", "Attempted"],
            "larg_vfo": ["Not VFO", "Not VFO", "VFO"],
            "larg_firearm": ["Not Firearm Charge", "Not Firearm Charge", "Top Charge is Firearm"],
            "charge_exposure_2022": [
                "comparison",
                "comparison",
                "2022_new_qualifying_firearm_charge",
            ],
            "charge_exposure_2023": ["comparison", "comparison", "comparison"],
        }
    )

    template = _charge_exposure_template(frame)

    first = template.iloc[0]
    assert first["total_cases"] == 2
    assert first["cases_2021"] == 1
    assert first["cases_2022"] == 1
    assert "amendment_2022_exposure" in template.columns


def test_charge_parsing_and_exposure_helpers_match_expected_rules():
    row_2022_gun = pd.Series(
        {
            "larg_charge": "PL 265.02   03",
            "larg_class": "D Felony",
            "charge_article": _charge_article("PL 265.02   03"),
            "charge_root": _charge_root("PL 265.02   03"),
            "charge_subdivision": _charge_subdivision("PL 265.02   03"),
            "pend_vfo": "No",
            "pend_nonvfo": "No",
            "pend_misd": "No",
            "any_pending_case": False,
        }
    )
    row_repeat = pd.Series(
        {
            "larg_charge": "PL 155.25",
            "larg_class": "A Misdemeanor",
            "charge_article": _charge_article("PL 155.25"),
            "charge_root": _charge_root("PL 155.25"),
            "charge_subdivision": _charge_subdivision("PL 155.25"),
            "pend_vfo": "No",
            "pend_nonvfo": "Yes",
            "pend_misd": "No",
            "any_pending_case": True,
        }
    )

    assert _charge_root("PL 265.01-B 01") == "PL 265.01-B"
    assert _charge_subdivision("PL 265.01-B 01") == "01"
    assert _charge_article("PL 155.25") == "155"
    assert _charge_exposure_2022(row_2022_gun) == "2022_new_qualifying_firearm_charge"
    assert _charge_exposure_2022(row_repeat) == "2022_repeat_harm_or_theft_proxy_candidate"
    assert _charge_exposure_2023(row_repeat) == "2023_repeat_offender_proxy_candidate"
    row_repeat["charge_exposure_2022"] = _charge_exposure_2022(row_repeat)
    row_repeat["charge_exposure_2023"] = _charge_exposure_2023(row_repeat)
    assert _row_exposure_2022(row_repeat) == "2022_repeat_harm_or_theft_proxy"
    assert _row_exposure_2023(row_repeat) == "2023_repeat_offender_proxy"


def test_severity_bucket_maps_felony_vfo_and_misdemeanor():
    frame = pd.DataFrame(
        {
            "larg_class": ["D Felony", "D Felony", "A Misdemeanor", "Violation"],
            "larg_vfo": ["VFO", "Not VFO", "Not VFO", ""],
        }
    )

    bucket = _severity_bucket(frame)

    assert bucket.tolist() == [
        "violent_felony",
        "non_violent_felony",
        "misdemeanor",
        "other",
    ]


def test_monthly_policy_tables_roll_up_expected_counts():
    frame = pd.DataFrame(
        {
            "caseid": ["1", "2", "3"],
            "court_type": ["NYC Criminal Courts", "NYC Criminal Courts", "NYC Criminal Courts"],
            "year_month": ["2022-05", "2022-05", "2022-06"],
            "arraign_year": [2022, 2022, 2022],
            "arraign_month": [5, 5, 6],
            "month_index_2022_05": [0, 0, 1],
            "month_index_2023_06": [-13, -13, -12],
            "larg_class": ["D Felony", "A Misdemeanor", "A Misdemeanor"],
            "larg_vfo": ["VFO", "Not VFO", "Not VFO"],
            "larg_firearm": ["Top Charge is Firearm", "Not Firearm Charge", "Not Firearm Charge"],
            "larg_rel_decision": ["ROR", "Bail Set", "Disposed at arraign"],
            "larg_rel_outcome": ["ROR", "BailNotPaid w/in 5days", ""],
            "disposition": ["Conviction", "Pending", "Dismissed"],
        }
    )

    release = _monthly_release_table(frame)
    disposition = _monthly_disposition_table(frame)
    windows = _amendment_window_summary(frame)

    assert release["total_cases"].sum() == 3
    assert int(disposition["conviction_or_yo"].sum()) == 1
    assert set(windows["policy_window"]) == {"amendment_2022_05", "amendment_2023_06"}


def test_policy_effect_tables_build_window_and_diff_outputs():
    frame = pd.DataFrame(
        {
            "caseid": ["1", "2", "3", "4", "5", "6", "7", "8"],
            "court_type": ["NYC Criminal Courts"] * 8,
            "month_index_2022_05": [-1, -1, 0, 0, -1, -1, 0, 0],
            "month_index_2023_06": [-13, -13, -12, -12, -13, -13, -12, -12],
            "row_exposure_2022": [
                "comparison",
                "comparison",
                "comparison",
                "comparison",
                "2022_new_qualifying_firearm_charge",
                "2022_new_qualifying_firearm_charge",
                "2022_new_qualifying_firearm_charge",
                "2022_new_qualifying_firearm_charge",
            ],
            "row_exposure_2023": ["comparison"] * 8,
            "larg_rel_decision": [
                "ROR",
                "Bail Set",
                "ROR",
                "Bail Set",
                "Bail Set",
                "Bail Set",
                "ROR",
                "ROR",
            ],
            "larg_rel_outcome": [
                "ROR",
                "BailNotPaid w/in 5days",
                "ROR",
                "BailNotPaid w/in 5days",
                "BailNotPaid w/in 5days",
                "BailNotPaid w/in 5days",
                "ROR",
                "ROR",
            ],
            "disposition": [
                "Conviction",
                "Pending",
                "Conviction",
                "Pending",
                "Conviction",
                "Conviction",
                "Dismissed",
                "Dismissed",
            ],
        }
    )

    windows = _policy_exposure_windows(frame)
    diffs = _policy_exposure_diffs(windows)

    assert set(windows["exposure_group"]) == {"comparison", "2022_new_qualifying_firearm_charge"}
    assert len(diffs) == 1
    assert diffs.iloc[0]["policy_window"] == "amendment_2022_05"
    assert diffs.iloc[0]["diff_vs_comparison_released_share_known"] == 1.0
