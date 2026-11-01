# Staging write evidence

Recorded on 2026-11-01 against a disposable local database: PostgreSQL 16.15 on Linux, database
`iris_test`, schema created from `sql/01_staging_ddl.sql`. This run did **not** use PostGIS
(see LIMITATIONS.md). The target table was a proposal, not the confirmed `iris_staging` DDL.

Command (twice in a row, same input):

```bash
export DB_URI=postgresql+psycopg://<user>@localhost:<port>/iris_test
python scripts/run_pipeline.py --write-db
```

## Run 1 (empty table)

```text
INFO cre72.validation: Validation finished: roofs in=3 valid=3 rejected=0 repaired=0
INFO cre72.database: Database upsert into iris_staging.portfolio_audit_staging: processed=3 inserted=3 updated=0 failed=0
```

## Run 2 (same input, idempotency)

```text
INFO cre72.database: Database upsert into iris_staging.portfolio_audit_staging: processed=3 inserted=0 updated=3 failed=0
```

## SQL checks (`sql/02_evidence_queries.sql`)

```text
 rows_in_staging
-----------------
               3

 property_id |   task_id   | as_of_date | annual_ppa_revenue_eur | walt_years | effective_ppa_term_years | geometry_crs
-------------+-------------+------------+------------------------+------------+--------------------------+--------------
 PROP-001    | TASK-CRE-72 | 2026-11-01 |                  86400 |        3.5 |                      3.5 | EPSG:25832
 PROP-002    | TASK-CRE-72 | 2026-11-01 |                  42000 |        2.5 |                      2.5 | EPSG:25832
 PROP-003    | TASK-CRE-72 | 2026-11-01 |                 119000 |       4.86 |                     4.86 | EPSG:25832

 table_schema |       table_name
--------------+-------------------------
 iris_staging | portfolio_audit_staging
```

Three rows after two runs, and the only user schema that contains a table is `iris_staging`.

## Error handling

| Case | Result |
|---|---|
| Target table does not exist | `RuntimeError: Target table does not exist: iris_staging.portfolio_audit_staging. Confirm the target DDL with Tariq before writing.` (nothing is created) |
| Database not reachable | connection error, non-zero exit (an unresponsive host is cut off by the 10 s connect timeout) |
| `DB_URI` not set | `RuntimeError: DB_URI is not configured` (covered by `tests/test_smoke_pipeline.py`) |
| Unknown column, null or duplicate key in the input | refused before any write (`tests/test_database.py`) |
| A batch fails during the write | counted in `failed`, logged, script exits with code 1 (tested with a CHECK constraint violation) |

## Automated checks

`pytest` against the same disposable database ran the integration tests and all passed:
first load inserts 3, second load updates 3 and inserts 0, a changed value is updated in place
(still 3 rows), only `iris_staging` is populated, a batch that violates a table constraint is counted
as failed with nothing written, and a missing table is reported and not created.
The tests refuse to run unless the database name contains `test`.

With `TEST_DB_URI` set all 46 tests pass. Without it the 6 database tests are skipped and the 40 other tests run.
