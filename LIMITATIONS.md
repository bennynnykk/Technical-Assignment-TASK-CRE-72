# Limitations and assumptions (TASK-CRE-72)

## Inaccessible or unverified external items

- **Target DDL not confirmed.** The task says to verify the expected DDL of
  `iris_staging.portfolio_audit_staging` with Tariq. I had no access to the real table, so
  `sql/01_staging_ddl.sql` is my proposal for a disposable local database. The loader reads whatever
  table actually exists and refuses to write on a mismatch (missing table, missing `property_id`
  key, unknown columns). It never creates or alters tables. If the real table differs, a column
  mapping is the one thing that would need adjusting.
- **PostGIS not exercised.** The recorded staging run used plain PostgreSQL 16.15 without the PostGIS
  extension. The proposed DDL stores roof outlines as WKT text with a `geometry_crs` column
  (`EPSG:25832`). If the confirmed DDL uses a PostGIS geometry column, the loader needs an
  `ST_GeomFromText(..., 25832)` mapping for that column. `docker-compose.yml` uses
  `postgis/postgis:16-3.4` for a PostGIS 3.4 test database.
- **No live services.** The module reads local CSV files only. No external endpoint, API, paging or
  rate limit is involved, so the timeout handling exists only for the database connection
  (10 s connect timeout, 30 s statement timeout).
- **No access to shared upstream data.** Nothing from `iris_core` or other production tables is read.

## Data and licenses

- All inputs in `data/raw/` and `tests/fixtures/defective/` are synthetic and labelled `mock`.
  They are not real properties, tenants or leases, and no real client portfolio data is included.
- Coordinates are plausible UTM 32N values near Hannover, but they are test geometries, not verified
  property locations.
- No third-party datasets are bundled, so no data license applies. If real cadastre, building
  footprint or irradiance data is used later, its license and attribution terms must be checked first.
- PV density and yield, PPA price and PPA term are illustrative assumptions, not market data.

## Spatial handling

- CRS is checked from the `crs` column of the input. A coordinate plausibility window for
  ETRS89 / UTM 32N (easting 166,000 to 834,000, northing 4.2 to 9.4 million) catches obvious
  mistakes such as latitude/longitude numbers labelled as EPSG:25832. It cannot prove that a
  coordinate really is in that CRS, and there is no reprojection. Input in another CRS is rejected.
- Invalid polygons are repaired with `shapely.make_valid()`. Roofs that are empty, unparseable,
  outside the window, or whose computed area differs from `roof_area_m2` by more than 1 percent are
  quarantined to `roofs_rejected.csv` with a reason, and the run continues.
- A property with no valid roof is excluded from the results and logged. Nothing is invented or
  substituted for it.

## Calculation limitations

- Annual aggregates only. No hourly generation/consumption matching, so self-consumption and PPA
  volume are likely overstated compared with a profile-based model.
- Revenue is gross. No CAPEX, OPEX, degradation, taxes, discounting, NPV or IRR. Contract revenue
  columns are simple undiscounted multiples.
- Surplus generation earns nothing (no feed-in tariff or BESS/HPC revenue).
- PPA demand counts only tenants with a lease running on the as-of date. Leases that expired or
  have not started are excluded.
- Effective PPA term is capped at the rent-weighted average remaining lease term (WALT). This is a
  conservative simplification: in practice a PPA could be tied to lease extensions, and tenants
  with short leases could be handled separately.
- The as-of date defaults to 2026-11-01 so results are reproducible. Remaining term uses
  365.25 days per year.
- Leases are assumed to be independent of each other (no renewal probability, no vacancy).

## Valuation limitations

- This module does **not** perform an ImmoWertV valuation, a highest-and-best-use value, or any
  GRZ/GFZ building-rights analysis. The "status quo vs optimization" comparison is limited to annual
  rent versus rent plus gross PV/PPA revenue.
- Nothing here is valuation advice. Outputs are illustrative screening figures.

## Database behaviour

- Writes target only `iris_staging.portfolio_audit_staging` (hard-coded). Upserts use
  `INSERT ... ON CONFLICT (property_id) DO UPDATE`, so reruns do not duplicate rows.
- Inserted vs updated rows are told apart with PostgreSQL's `xmax = 0` marker, which is a
  PostgreSQL implementation detail. If the confirmed table is different, this count should be
  re-checked.
- A failed batch is counted and logged, and the script exits with a non-zero code.
