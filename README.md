# TASK-CRE-72: Commercial Rooftop PV & Onsite Tenant PPA Revenue Calculator

Wave 4 module for the reverse CRE portfolio audit. For each property it estimates rooftop PV
generation, how much of it tenants could buy under an onsite PPA, and compares the status quo
(rent only) with PV + PPA. The PPA term is capped by the lease situation (WALT), because a PPA
cannot reliably run longer than the tenants' leases.

All sample data is synthetic. No client data and no credentials are in this repository.

Read first: [LIMITATIONS.md](LIMITATIONS.md) (assumptions, unverified items, licenses),
[docs/SCHEMA_MAPPING.md](docs/SCHEMA_MAPPING.md) (inputs to outputs to table columns),
[docs/STAGING_EVIDENCE.md](docs/STAGING_EVIDENCE.md) (staging writes, row counts, idempotency).

## What it does

1. Loads five CSV inputs: properties, roofs, tenants, leases, PPA assumptions.
2. Validates them (keys, numeric ranges, foreign keys, lease dates).
3. Validates roof geometry: EPSG:25832 label, plausibility window for UTM zone 32N coordinates,
   `shapely.make_valid()` for invalid polygons, empty or unrepairable features are quarantined
   (written to `roofs_rejected.csv` with a reason) instead of stopping the run.
4. Calculates PV capacity and annual generation per property.
5. Calculates PPA volume and revenue using only tenants with an active lease on the as-of date,
   plus lease metrics (active rent, WALT, effective PPA term) and a status quo vs PV + PPA comparison.
6. Optionally upserts the result into `iris_staging.portfolio_audit_staging`.

Every step logs processed / valid / rejected counts, and the database step logs
processed / inserted / updated / failed.

## Quick start

Python 3.11+ (tests pass and outputs are byte-identical on 3.11, 3.12 and 3.13).

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py
pytest -q
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_pipeline.py
pytest -q
```

Outputs go to `data/processed/` (git-ignored): `ppa_results.csv`, `pv_results.csv`,
`validation_report.json`, `roofs_rejected.csv`, `run_summary.json`, `*_validated.csv`.
Committed examples are in `samples/`.

Useful options:

```bash
python scripts/run_pipeline.py --data-dir tests/fixtures/defective --output-dir /tmp/out   # defective inputs
python scripts/run_pipeline.py --as-of 2027-01-01                                          # other valuation date
```

The valuation date defaults to 2026-11-01 (fixed, so reruns are identical). Override with
`--as-of` or the `AS_OF_DATE` environment variable.

## Docker

```bash
docker build -t task-cre-72 .
docker run --rm task-cre-72                      # full pipeline on the bundled synthetic data
docker run --rm task-cre-72 pytest -q            # tests (DB tests skip without TEST_DB_URI)
```

## Database (staging only)

The only write target is `iris_staging.portfolio_audit_staging`. It is hard-coded in
`src/cre72/database.py`, not configurable. The loader never creates or alters tables: it reflects
the existing table and refuses to write if the table is missing, has no primary key containing
`property_id`, or lacks any column the results contain.

The expected table DDL is **not confirmed with Tariq yet**. `sql/01_staging_ddl.sql` is a proposal
for a disposable local database only.

Local PostgreSQL 16 / PostGIS 3.4 test database:

```bash
docker compose up -d db                                   # creates iris_staging from sql/01_staging_ddl.sql
cp .env.example .env                                      # DB_URI for localhost
python scripts/run_pipeline.py --write-db                 # run twice to see idempotency in the logs
docker compose down -v
```

Connection string comes from the `DB_URI` environment variable (driver prefix
`postgresql+psycopg://`). Nothing is hard-coded and `.env` is git-ignored.

Integration tests (disposable database whose name contains `test`):

```bash
TEST_DB_URI=postgresql+psycopg://user:pw@localhost:5432/iris_test pytest -m integration
```

## Calculation logic

Per property, as of the valuation date:

| Quantity | Formula |
|---|---|
| PV capacity (kWp) | usable roof area (m2) x PV density (kWp/m2), summed over valid roofs |
| Annual generation (kWh) | capacity x annual yield (kWh/kWp) |
| Tenant demand (kWh) | sum of demand of tenants with an active lease |
| PPA volume (kWh) | min(generation, tenant demand) |
| Annual PPA revenue (EUR) | PPA volume x PPA price (gross, before CAPEX/OPEX) |
| WALT (years) | sum(rent x remaining lease years) / sum(rent) over active leases |
| Effective PPA term (years) | min(nominal PPA term, WALT) |
| Nominal contract revenue | annual PPA revenue x nominal term |
| Lease-capped contract revenue | annual PPA revenue x effective term (undiscounted) |
| Status quo income | active annual rent |
| PV + PPA gross income | active annual rent + annual PPA revenue |

These are annual aggregates. There is no hourly generation/consumption matching, no discounting,
no CAPEX/OPEX, no degradation, no grid export revenue.

## Project layout

```text
src/cre72/        config, loading, validation, PV, PPA, lease analysis, database, pipeline
scripts/          run_pipeline.py, write_to_database.py, generate_sample_data.py
tests/            unit, smoke and (optional) database integration tests; fixtures/defective
data/raw/         small synthetic input set
samples/          example outputs for the sample data and for the defective fixture
sql/              proposed staging DDL and evidence queries
docs/             schema mapping and staging evidence
```

## Task checklist

| Requirement | Where |
|---|---|
| Python 3.11+, Dockerfile, dependencies | `Dockerfile`, `requirements.txt` |
| Staging-only writes, `DB_URI`, idempotent upsert, duplicate protection | `src/cre72/database.py`, `docs/STAGING_EVIDENCE.md` |
| EPSG:25832, `make_valid`, empty/invalid handling | `src/cre72/validation.py`, `tests/test_validation.py` |
| Logged processed / inserted / failed counts | `src/cre72/pipeline.py`, `src/cre72/database.py` |
| Fixture, smoke tests, output samples, schema mapping | `tests/`, `samples/`, `docs/SCHEMA_MAPPING.md` |
| Limitations note | `LIMITATIONS.md` |
