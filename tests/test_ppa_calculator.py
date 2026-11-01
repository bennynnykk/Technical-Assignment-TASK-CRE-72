import pandas as pd
import pytest

from cre72.ppa_calculator import calculate_ppa_revenue


def _inputs(demand=15000):
    pv = pd.DataFrame([
        {
            "property_id": "PROP-001",
            "usable_roof_area_m2": 100,
            "pv_capacity_kwp": 20,
            "annual_generation_kwh": 19000,
        }
    ])

    tenants = pd.DataFrame([
        {
            "tenant_id": "TEN-001",
            "property_id": "PROP-001",
            "annual_demand_kwh": demand,
        }
    ])

    assumptions = pd.DataFrame([
        {
            "property_id": "PROP-001",
            "ppa_price_eur_per_kwh": 0.2,
            "ppa_term_years": 15,
        }
    ])

    return pv, tenants, assumptions


def test_ppa_revenue():
    pv, tenants, assumptions = _inputs()

    result = calculate_ppa_revenue(pv, tenants, assumptions)

    assert result.loc[0, "ppa_volume_kwh"] == 15000
    assert result.loc[0, "surplus_energy_kwh"] == 4000
    assert result.loc[0, "annual_ppa_revenue_eur"] == 3000
    assert result.loc[0, "nominal_contract_revenue_eur"] == 45000


def test_demand_above_generation_is_capped_by_generation():
    pv, tenants, assumptions = _inputs(demand=50000)

    result = calculate_ppa_revenue(pv, tenants, assumptions)

    assert result.loc[0, "ppa_volume_kwh"] == 19000
    assert result.loc[0, "uncovered_tenant_demand_kwh"] == 31000
    assert result.loc[0, "surplus_energy_kwh"] == 0


def test_property_without_tenants_has_zero_revenue():
    pv, tenants, assumptions = _inputs()
    tenants = tenants.iloc[0:0]

    result = calculate_ppa_revenue(pv, tenants, assumptions)

    assert result.loc[0, "ppa_volume_kwh"] == 0
    assert result.loc[0, "annual_ppa_revenue_eur"] == 0
    assert pd.isna(result.loc[0, "tenant_demand_coverage_ratio"])


def test_ppa_term_is_capped_by_lease_walt():
    pv, tenants, assumptions = _inputs()

    leases = pd.DataFrame([
        {
            "lease_id": "L1",
            "tenant_id": "TEN-001",
            "property_id": "PROP-001",
            "start_date": "2020-01-01",
            "end_date": "2028-11-01",
            "annual_rent_eur": 10000,
        }
    ])

    result = calculate_ppa_revenue(
        pv, tenants, assumptions, leases=leases, as_of="2026-11-01"
    )

    # 2026-11-01 to 2028-11-01 is 731 days = about 2.0 years
    assert result.loc[0, "walt_years"] == pytest.approx(2.0, abs=0.01)
    assert result.loc[0, "effective_ppa_term_years"] == pytest.approx(2.0, abs=0.01)
    assert result.loc[0, "lease_capped_contract_revenue_eur"] == pytest.approx(
        3000 * 2.0, abs=40
    )
    assert result.loc[0, "status_quo_annual_income_eur"] == 10000
    assert result.loc[0, "optimized_annual_gross_income_eur"] == 13000
    assert result.loc[0, "annual_income_uplift_pct"] == pytest.approx(30.0)


def test_expired_lease_tenant_is_excluded_from_demand():
    pv, tenants, assumptions = _inputs()

    leases = pd.DataFrame([
        {
            "lease_id": "L1",
            "tenant_id": "TEN-001",
            "property_id": "PROP-001",
            "start_date": "2015-01-01",
            "end_date": "2025-12-31",
            "annual_rent_eur": 10000,
        }
    ])

    result = calculate_ppa_revenue(
        pv, tenants, assumptions, leases=leases, as_of="2026-11-01"
    )

    assert result.loc[0, "total_tenant_demand_kwh"] == 0
    assert result.loc[0, "annual_ppa_revenue_eur"] == 0
    assert result.loc[0, "active_lease_count"] == 0
    assert result.loc[0, "effective_ppa_term_years"] == 0


def test_leases_require_as_of_date():
    pv, tenants, assumptions = _inputs()
    leases = pd.DataFrame(columns=[
        "lease_id", "tenant_id", "property_id",
        "start_date", "end_date", "annual_rent_eur",
    ])

    with pytest.raises(ValueError):
        calculate_ppa_revenue(pv, tenants, assumptions, leases=leases)
