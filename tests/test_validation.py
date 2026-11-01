import pandas as pd
import pytest

from cre72.data_loader import load_datasets
from cre72.validation import (
    check_roof_row,
    validate_dates,
    validate_datasets,
    validate_foreign_keys,
    validate_roofs,
    validate_unique_keys,
)


GOOD_WKT = "POLYGON ((550000 5800000, 550100 5800000, 550100 5800060, 550000 5800060, 550000 5800000))"
BOWTIE_WKT = "POLYGON ((550500 5800500, 550600 5800600, 550600 5800500, 550500 5800600, 550500 5800500))"


def _roof(**overrides):
    row = {
        "roof_id": "R1",
        "property_id": "P1",
        "roof_area_m2": 6000,
        "usable_roof_area_m2": 4500,
        "geometry_wkt": GOOD_WKT,
        "crs": "EPSG:25832",
    }
    row.update(overrides)
    return pd.Series(row)


def test_duplicate_keys_are_rejected():
    df = pd.DataFrame({
        "property_id": ["PROP-001", "PROP-001"]
    })

    with pytest.raises(ValueError):
        validate_unique_keys(
            df,
            "property_id",
            "properties",
        )


def test_unique_keys_are_accepted():
    df = pd.DataFrame({
        "property_id": ["PROP-001", "PROP-002"]
    })

    validate_unique_keys(
        df,
        "property_id",
        "properties",
    )


def test_null_keys_are_rejected():
    df = pd.DataFrame({"property_id": ["PROP-001", None]})

    with pytest.raises(ValueError):
        validate_unique_keys(df, "property_id", "properties")


def test_valid_roof_is_accepted():
    wkt_out, area, repaired, reason = check_roof_row(_roof())

    assert reason is None
    assert repaired is False
    assert area == pytest.approx(6000)


def test_self_intersecting_roof_is_repaired_with_make_valid():
    row = _roof(geometry_wkt=BOWTIE_WKT, roof_area_m2=5000, usable_roof_area_m2=3500)

    wkt_out, area, repaired, reason = check_roof_row(row)

    assert reason is None
    assert repaired is True
    assert area == pytest.approx(5000)
    assert wkt_out.startswith("MULTIPOLYGON")


def test_wrong_crs_is_rejected():
    _, _, _, reason = check_roof_row(_roof(crs="EPSG:4326"))

    assert "CRS" in reason


def test_empty_geometry_is_rejected():
    _, _, _, reason = check_roof_row(_roof(geometry_wkt="POLYGON EMPTY"))

    assert reason == "empty geometry"


def test_unparseable_wkt_is_rejected():
    _, _, _, reason = check_roof_row(_roof(geometry_wkt="not a geometry"))

    assert "unparseable" in reason


def test_missing_geometry_is_rejected():
    _, _, _, reason = check_roof_row(_roof(geometry_wkt=None))

    assert reason == "missing geometry"


def test_lat_lon_numbers_labelled_as_utm_are_rejected():
    wkt = "POLYGON ((9.7 52.3, 9.8 52.3, 9.8 52.4, 9.7 52.4, 9.7 52.3))"

    _, _, _, reason = check_roof_row(_roof(geometry_wkt=wkt, roof_area_m2=1000, usable_roof_area_m2=500))

    assert "plausibility" in reason


def test_area_mismatch_is_rejected():
    _, _, _, reason = check_roof_row(_roof(roof_area_m2=9000, usable_roof_area_m2=100))

    assert "differs" in reason


def test_usable_area_above_total_is_rejected():
    _, _, _, reason = check_roof_row(_roof(usable_roof_area_m2=7000))

    assert "usable" in reason


def test_bad_rows_are_quarantined_not_fatal():
    roofs = pd.DataFrame([
        _roof(roof_id="OK").to_dict(),
        _roof(roof_id="BAD", crs="EPSG:4326").to_dict(),
        _roof(
            roof_id="FIXED",
            geometry_wkt=BOWTIE_WKT,
            roof_area_m2=5000,
            usable_roof_area_m2=3500,
        ).to_dict(),
    ])

    valid, rejected, repaired = validate_roofs(roofs)

    assert sorted(valid["roof_id"]) == ["FIXED", "OK"]
    assert list(rejected["roof_id"]) == ["BAD"]
    assert repaired == 1


def test_unknown_property_in_child_table_is_rejected():
    datasets = load_datasets()
    datasets["tenants"].loc[0, "property_id"] = "PROP-999"

    with pytest.raises(ValueError):
        validate_foreign_keys(datasets)


def test_lease_ending_before_start_is_rejected():
    leases = pd.DataFrame([
        {"start_date": "2025-01-01", "end_date": "2024-01-01"}
    ])

    with pytest.raises(ValueError):
        validate_dates(leases)


def test_missing_required_column_is_rejected(sample_data_dir):
    datasets = load_datasets(sample_data_dir)
    datasets["roofs"] = datasets["roofs"].drop(columns=["crs"])

    with pytest.raises(ValueError, match="missing columns"):
        validate_datasets(datasets)


def test_missing_input_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_datasets(tmp_path)


def test_report_counts_for_defective_fixture(defective_data_dir):
    datasets, report = validate_datasets(load_datasets(defective_data_dir))

    assert report["datasets"]["roofs"]["rows_in"] == 5
    assert report["datasets"]["roofs"]["rows_valid"] == 2
    assert report["datasets"]["roofs"]["rows_rejected"] == 3
    assert report["repaired_geometries"] == 1
    assert report["properties_without_valid_roof"] == ["PROP-003"]
