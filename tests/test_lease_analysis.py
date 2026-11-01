import pandas as pd
import pytest

from cre72.lease_analysis import active_leases, lease_metrics


def _leases():
    return pd.DataFrame([
        {"lease_id": "L1", "tenant_id": "T1", "property_id": "P1",
         "start_date": "2020-01-01", "end_date": "2030-11-01", "annual_rent_eur": 300},
        {"lease_id": "L2", "tenant_id": "T2", "property_id": "P1",
         "start_date": "2020-01-01", "end_date": "2028-11-01", "annual_rent_eur": 100},
        {"lease_id": "L3", "tenant_id": "T3", "property_id": "P1",
         "start_date": "2010-01-01", "end_date": "2020-12-31", "annual_rent_eur": 999},
        {"lease_id": "L4", "tenant_id": "T4", "property_id": "P1",
         "start_date": "2027-01-01", "end_date": "2035-12-31", "annual_rent_eur": 999},
    ])


def test_only_running_leases_are_active():
    active = active_leases(_leases(), "2026-11-01")

    assert sorted(active["lease_id"]) == ["L1", "L2"]


def test_walt_is_rent_weighted():
    metrics = lease_metrics(_leases(), "2026-11-01")

    row = metrics.iloc[0]

    # L1 ~4.0 years at 300, L2 ~2.0 years at 100 -> (300*4 + 100*2) / 400 = 3.5
    assert row["active_lease_count"] == 2
    assert row["active_annual_rent_eur"] == 400
    assert row["walt_years"] == pytest.approx(3.5, abs=0.02)


def test_no_active_leases_gives_empty_metrics():
    metrics = lease_metrics(_leases(), "2040-01-01")

    assert metrics.empty
