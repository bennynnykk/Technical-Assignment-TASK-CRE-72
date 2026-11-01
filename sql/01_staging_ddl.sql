-- PROPOSED DDL for a LOCAL / DISPOSABLE test database only.
--
-- The real iris_staging.portfolio_audit_staging DDL has NOT been confirmed with Tariq
-- (the task asks to verify it). This file documents the shape the code writes.
-- Do NOT run it against a shared database. The loader never creates or alters tables:
-- it reflects whatever table exists and refuses to write if columns or the key differ.
--
-- Spatial note: roof outlines are kept as WKT text plus an explicit geometry_crs column
-- (always 'EPSG:25832') so this file works on plain PostgreSQL. If the confirmed DDL uses a
-- PostGIS column, e.g. geometry(MultiPolygon, 25832), the loader needs a small ST_GeomFromText
-- mapping for that column (listed as a known limitation).

CREATE SCHEMA IF NOT EXISTS iris_staging;

CREATE TABLE IF NOT EXISTS iris_staging.portfolio_audit_staging (
    property_id                        text PRIMARY KEY,
    task_id                            text NOT NULL,
    as_of_date                         date NOT NULL,
    data_source                        text,
    roof_count                         integer,
    usable_roof_area_m2                numeric,
    pv_capacity_kwp                    numeric,
    annual_generation_kwh              numeric,
    total_tenant_demand_kwh            numeric,
    ppa_price_eur_per_kwh              numeric,
    ppa_term_years                     numeric,
    ppa_volume_kwh                     numeric,
    surplus_energy_kwh                 numeric,
    uncovered_tenant_demand_kwh        numeric,
    tenant_demand_coverage_ratio       numeric,
    annual_ppa_revenue_eur             numeric,
    nominal_contract_revenue_eur       numeric,
    active_lease_count                 integer,
    active_annual_rent_eur             numeric,
    walt_years                         numeric,
    effective_ppa_term_years           numeric,
    lease_capped_contract_revenue_eur  numeric,
    status_quo_annual_income_eur       numeric,
    optimized_annual_gross_income_eur  numeric,
    annual_income_uplift_pct           numeric,
    roof_geometry_wkt                  text,
    geometry_crs                       text CHECK (geometry_crs = 'EPSG:25832'),
    updated_at                         timestamptz NOT NULL DEFAULT now()
);
