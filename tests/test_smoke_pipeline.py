import json

import pandas as pd
import pytest

from datetime import date

from cre72.pipeline import RESULT_COLUMNS, run_pipeline


AS_OF = date(2026, 11, 1)


def test_sample_data_end_to_end(sample_data_dir, tmp_path):
    summary, results = run_pipeline(
        data_dir=sample_data_dir, output_dir=tmp_path, as_of=AS_OF
    )

    assert summary["properties_in"] == 3
    assert summary["properties_with_results"] == 3
    assert summary["roofs_rejected"] == 0

    assert list(results.columns) == RESULT_COLUMNS
    assert (results["geometry_crs"] == "EPSG:25832").all()
    assert (results["task_id"] == "TASK-CRE-72").all()

    prop1 = results.set_index("property_id").loc["PROP-001"]

    # 4500 m2 * 0.2 kWp/m2 * 950 kWh/kWp = 855,000 kWh; demand 480,000 kWh caps volume
    assert prop1["annual_generation_kwh"] == 855000
    assert prop1["ppa_volume_kwh"] == 480000
    assert prop1["annual_ppa_revenue_eur"] == pytest.approx(86400)

    for name in [
        "pv_results.csv",
        "ppa_results.csv",
        "validation_report.json",
        "run_summary.json",
        "roofs_validated.csv",
        "roofs_rejected.csv",
    ]:
        assert (tmp_path / name).exists(), name


def test_rerun_is_idempotent(sample_data_dir, tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    run_pipeline(data_dir=sample_data_dir, output_dir=first_dir, as_of=AS_OF)
    run_pipeline(data_dir=sample_data_dir, output_dir=second_dir, as_of=AS_OF)

    first = (first_dir / "ppa_results.csv").read_text(encoding="utf-8")
    second = (second_dir / "ppa_results.csv").read_text(encoding="utf-8")

    assert first == second


def test_defective_fixture_still_produces_results(defective_data_dir, tmp_path):
    summary, results = run_pipeline(
        data_dir=defective_data_dir, output_dir=tmp_path, as_of=AS_OF
    )

    assert summary["roofs_rejected"] == 3
    assert summary["geometries_repaired"] == 1
    assert summary["properties_with_results"] == 2
    assert set(results["property_id"]) == {"PROP-001", "PROP-002"}

    rejected = pd.read_csv(tmp_path / "roofs_rejected.csv")
    assert set(rejected["roof_id"]) == {"ROOF-003", "ROOF-004", "ROOF-005"}

    report = json.loads((tmp_path / "validation_report.json").read_text())
    assert len(report["roofs_rejected"]) == 3

    # TEN-004's lease expired on 2026-06-30, so only TEN-003 (120,000 kWh) counts for PROP-002
    prop2 = results.set_index("property_id").loc["PROP-002"]
    assert prop2["total_tenant_demand_kwh"] == 120000
    assert prop2["active_lease_count"] == 1


def test_write_db_requires_db_uri(sample_data_dir, tmp_path, monkeypatch):
    monkeypatch.delenv("DB_URI", raising=False)

    with pytest.raises(RuntimeError, match="DB_URI"):
        run_pipeline(
            data_dir=sample_data_dir,
            output_dir=tmp_path,
            as_of=AS_OF,
            write_db=True,
        )
