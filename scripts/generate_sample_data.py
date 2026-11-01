from pathlib import Path

import pandas as pd


# --------------------------------------------------
# 1. Project configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)



# --------------------------------------------------
# 2. Properties dataset
# --------------------------------------------------

properties = pd.DataFrame([
    {
        "property_id": "PROP-001",
        "property_name": "Industrial Warehouse",
        "property_type": "Warehouse",
        "city": "Hannover",
        "country": "Germany",
        "land_area_m2": 12000,
        "building_area_m2": 6000,
        "easting_m": 550050,
        "northing_m": 5800030,
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
    {
        "property_id": "PROP-002",
        "property_name": "Office Building",
        "property_type": "Office",
        "city": "Hannover",
        "country": "Germany",
        "land_area_m2": 5000,
        "building_area_m2": 2500,
        "easting_m": 550525,
        "northing_m": 5800525,
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
    {
        "property_id": "PROP-003",
        "property_name": "Logistics Center",
        "property_type": "Logistics",
        "city": "Hannover",
        "country": "Germany",
        "land_area_m2": 18000,
        "building_area_m2": 9000,
        "easting_m": 551050,
        "northing_m": 5801045,
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
])


# --------------------------------------------------
# 3. Roof dataset
# --------------------------------------------------

def create_rectangle_wkt(x, y, width, height):
    """
    Create a rectangular polygon in WKT format.
    Coordinates use EPSG:25832.
    """

    return (
        f"POLYGON (("
        f"{x} {y}, "
        f"{x + width} {y}, "
        f"{x + width} {y + height}, "
        f"{x} {y + height}, "
        f"{x} {y}"
        f"))"
    )


roofs = pd.DataFrame([
    {
        "roof_id": "ROOF-001",
        "property_id": "PROP-001",
        "roof_area_m2": 6000,
        "usable_roof_area_m2": 4500,
        "roof_type": "Flat",
        "roof_condition": "Good",
        "geometry_wkt": create_rectangle_wkt(
            550000, 5800000, 100, 60
        ),
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
    {
        "roof_id": "ROOF-002",
        "property_id": "PROP-002",
        "roof_area_m2": 2500,
        "usable_roof_area_m2": 1750,
        "roof_type": "Flat",
        "roof_condition": "Good",
        "geometry_wkt": create_rectangle_wkt(
            550500, 5800500, 50, 50
        ),
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
    {
        "roof_id": "ROOF-003",
        "property_id": "PROP-003",
        "roof_area_m2": 9000,
        "usable_roof_area_m2": 7200,
        "roof_type": "Flat",
        "roof_condition": "Good",
        "geometry_wkt": create_rectangle_wkt(
            551000, 5801000, 100, 90
        ),
        "crs": "EPSG:25832",
        "data_source": "mock",
    },
])


# --------------------------------------------------
# 4. Tenants dataset
# --------------------------------------------------

tenants = pd.DataFrame([
    {
        "tenant_id": "TEN-001",
        "property_id": "PROP-001",
        "tenant_name": "Tenant A",
        "annual_demand_kwh": 300000,
        "data_source": "mock",
    },
    {
        "tenant_id": "TEN-002",
        "property_id": "PROP-001",
        "tenant_name": "Tenant B",
        "annual_demand_kwh": 180000,
        "data_source": "mock",
    },
    {
        "tenant_id": "TEN-003",
        "property_id": "PROP-002",
        "tenant_name": "Tenant C",
        "annual_demand_kwh": 120000,
        "data_source": "mock",
    },
    {
        "tenant_id": "TEN-004",
        "property_id": "PROP-002",
        "tenant_name": "Tenant D",
        "annual_demand_kwh": 90000,
        "data_source": "mock",
    },
    {
        "tenant_id": "TEN-005",
        "property_id": "PROP-003",
        "tenant_name": "Tenant E",
        "annual_demand_kwh": 450000,
        "data_source": "mock",
    },
    {
        "tenant_id": "TEN-006",
        "property_id": "PROP-003",
        "tenant_name": "Tenant F",
        "annual_demand_kwh": 250000,
        "data_source": "mock",
    },
])


# --------------------------------------------------
# 5. Lease dataset
# --------------------------------------------------

leases = pd.DataFrame([
    {
        "lease_id": "LEASE-001",
        "property_id": "PROP-001",
        "tenant_id": "TEN-001",
        "start_date": "2023-01-01",
        "end_date": "2030-12-31",
        "annual_rent_eur": 240000,
    },
    {
        "lease_id": "LEASE-002",
        "property_id": "PROP-001",
        "tenant_id": "TEN-002",
        "start_date": "2024-01-01",
        "end_date": "2028-12-31",
        "annual_rent_eur": 120000,
    },
    {
        "lease_id": "LEASE-003",
        "property_id": "PROP-002",
        "tenant_id": "TEN-003",
        "start_date": "2022-01-01",
        "end_date": "2029-12-31",
        "annual_rent_eur": 180000,
    },
    {
        "lease_id": "LEASE-004",
        "property_id": "PROP-002",
        "tenant_id": "TEN-004",
        "start_date": "2025-01-01",
        "end_date": "2027-12-31",
        "annual_rent_eur": 90000,
    },
    {
        "lease_id": "LEASE-005",
        "property_id": "PROP-003",
        "tenant_id": "TEN-005",
        "start_date": "2023-06-01",
        "end_date": "2032-05-31",
        "annual_rent_eur": 360000,
    },
    {
        "lease_id": "LEASE-006",
        "property_id": "PROP-003",
        "tenant_id": "TEN-006",
        "start_date": "2024-06-01",
        "end_date": "2030-05-31",
        "annual_rent_eur": 200000,
    },
])


# --------------------------------------------------
# 6. PPA assumptions dataset
# --------------------------------------------------

ppa_assumptions = pd.DataFrame([
    {
        "property_id": "PROP-001",
        "ppa_price_eur_per_kwh": 0.18,
        "pv_density_kwp_per_m2": 0.20,
        "annual_yield_kwh_per_kwp": 950,
        "ppa_term_years": 15,
        "dataset_type": "illustrative",
    },
    {
        "property_id": "PROP-002",
        "ppa_price_eur_per_kwh": 0.20,
        "pv_density_kwp_per_m2": 0.20,
        "annual_yield_kwh_per_kwp": 900,
        "ppa_term_years": 15,
        "dataset_type": "illustrative",
    },
    {
        "property_id": "PROP-003",
        "ppa_price_eur_per_kwh": 0.17,
        "pv_density_kwp_per_m2": 0.20,
        "annual_yield_kwh_per_kwp": 950,
        "ppa_term_years": 15,
        "dataset_type": "illustrative",
    },
])


# --------------------------------------------------
# 7. Export CSV files
# --------------------------------------------------

datasets = {
    "properties.csv": properties,
    "roofs.csv": roofs,
    "tenants.csv": tenants,
    "leases.csv": leases,
    "ppa_assumptions.csv": ppa_assumptions,
}

for filename, dataframe in datasets.items():

    output_path = OUTPUT_DIR / filename

    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8",
    )

    print(
        f"Created {filename}: "
        f"{len(dataframe)} rows"
    )


# --------------------------------------------------
# 8. Dataset summary
# --------------------------------------------------

print("\nDataset generation completed.")

print(f"Output directory: {OUTPUT_DIR}")

print("\nDataset summary:")

for filename, dataframe in datasets.items():
    print(f"{filename}: {len(dataframe)} rows")