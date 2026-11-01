# Schema mapping

Inputs are CSV files in `data/raw/` (same layout for `tests/fixtures/defective/`).
The results are written to `ppa_results.csv`, and the same columns map one to one to the proposed
staging table in `sql/01_staging_ddl.sql`. The key is `property_id`.

## Inputs

| File | Key | Columns used |
|---|---|---|
| properties.csv | property_id | property_type, land_area_m2, building_area_m2, easting_m, northing_m, crs, data_source |
| roofs.csv | roof_id | property_id, roof_area_m2, usable_roof_area_m2, geometry_wkt, crs |
| tenants.csv | tenant_id | property_id, annual_demand_kwh |
| leases.csv | lease_id | tenant_id, property_id, start_date, end_date, annual_rent_eur |
| ppa_assumptions.csv | property_id | ppa_price_eur_per_kwh, pv_density_kwp_per_m2, annual_yield_kwh_per_kwp, ppa_term_years |

## Output columns (ppa_results.csv and staging table)

| Column | Type | Source / formula |
|---|---|---|
| property_id | text, PK | properties.property_id |
| task_id | text | constant `TASK-CRE-72` |
| as_of_date | date | valuation date (default 2026-11-01) |
| data_source | text | properties.data_source (`mock` for the sample data) |
| roof_count | integer | number of valid roofs of the property |
| usable_roof_area_m2 | numeric | sum of usable_roof_area_m2 over valid roofs |
| pv_capacity_kwp | numeric | usable area x pv_density_kwp_per_m2 |
| annual_generation_kwh | numeric | capacity x annual_yield_kwh_per_kwp |
| total_tenant_demand_kwh | numeric | demand of tenants with an active lease |
| ppa_price_eur_per_kwh | numeric | ppa_assumptions |
| ppa_term_years | numeric | ppa_assumptions (nominal term) |
| ppa_volume_kwh | numeric | min(generation, tenant demand) |
| surplus_energy_kwh | numeric | generation - PPA volume (not monetised) |
| uncovered_tenant_demand_kwh | numeric | tenant demand - PPA volume |
| tenant_demand_coverage_ratio | numeric | PPA volume / tenant demand (null if no demand) |
| annual_ppa_revenue_eur | numeric | PPA volume x price (gross) |
| nominal_contract_revenue_eur | numeric | annual revenue x nominal term |
| active_lease_count | integer | leases running on the as-of date |
| active_annual_rent_eur | numeric | sum of rent of active leases |
| walt_years | numeric | rent-weighted remaining lease term of active leases |
| effective_ppa_term_years | numeric | min(nominal term, WALT) |
| lease_capped_contract_revenue_eur | numeric | annual revenue x effective term |
| status_quo_annual_income_eur | numeric | active annual rent |
| optimized_annual_gross_income_eur | numeric | active rent + annual PPA revenue |
| annual_income_uplift_pct | numeric | annual PPA revenue / active rent x 100 |
| roof_geometry_wkt | text | union of validated roof polygons, EPSG:25832 |
| geometry_crs | text | constant `EPSG:25832` (checked in the DDL) |
| updated_at | timestamptz | set by the database on insert and on update |

## Other outputs

| File | Content |
|---|---|
| pv_results.csv | per property PV capacity and generation, roof outline |
| validation_report.json | row counts in / valid / rejected per dataset, repaired geometries, rejected roofs with reason, properties without a valid roof |
| roofs_rejected.csv | quarantined roof rows plus `rejection_reason` |
| run_summary.json | counts of the whole run, including database counts if `--write-db` was used |
| *_validated.csv | inputs after validation (roofs with `geometry_area_m2`, `geometry_repaired`) |

Examples: `samples/sample_data/` and `samples/defective_fixture/`.
