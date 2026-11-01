import pandas as pd
import pytest

from cre72.pv_calculator import calculate_pv_potential


def test_pv_calculation():
    roofs = pd.DataFrame([
        {
            "property_id": "PROP-001",
            "usable_roof_area_m2": 100,
        }
    ])

    assumptions = pd.DataFrame([
        {
            "property_id": "PROP-001",
            "pv_density_kwp_per_m2": 0.2,
            "annual_yield_kwh_per_kwp": 950,
        }
    ])

    result = calculate_pv_potential(roofs, assumptions)

    assert result.loc[0, "pv_capacity_kwp"] == 20
    assert result.loc[0, "annual_generation_kwh"] == 19000


def test_multiple_roofs_are_summed_and_outline_is_merged():
    roofs = pd.DataFrame([
        {
            "roof_id": "R1",
            "property_id": "PROP-001",
            "usable_roof_area_m2": 100,
            "geometry_wkt": "POLYGON ((550000 5800000, 550010 5800000, 550010 5800010, 550000 5800010, 550000 5800000))",
        },
        {
            "roof_id": "R2",
            "property_id": "PROP-001",
            "usable_roof_area_m2": 50,
            "geometry_wkt": "POLYGON ((550010 5800000, 550020 5800000, 550020 5800010, 550010 5800010, 550010 5800000))",
        },
    ])

    assumptions = pd.DataFrame([
        {
            "property_id": "PROP-001",
            "pv_density_kwp_per_m2": 0.2,
            "annual_yield_kwh_per_kwp": 1000,
        }
    ])

    result = calculate_pv_potential(roofs, assumptions)

    assert len(result) == 1
    assert result.loc[0, "roof_count"] == 2
    assert result.loc[0, "pv_capacity_kwp"] == pytest.approx(30)
    assert result.loc[0, "geometry_crs"] == "EPSG:25832"
    assert result.loc[0, "roof_geometry_wkt"].startswith("POLYGON")


def test_no_matching_assumptions_raises():
    roofs = pd.DataFrame([{"property_id": "PROP-001", "usable_roof_area_m2": 10}])
    assumptions = pd.DataFrame([
        {
            "property_id": "PROP-999",
            "pv_density_kwp_per_m2": 0.2,
            "annual_yield_kwh_per_kwp": 950,
        }
    ])

    with pytest.raises(ValueError):
        calculate_pv_potential(roofs, assumptions)
