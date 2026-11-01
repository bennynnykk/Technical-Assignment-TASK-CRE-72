-- Example queries used to show staging-only persistence and idempotency.
-- Run against the disposable test database after scripts/write_to_database.py.

-- 1. Row count (expect 3 for the sample data, also after a second run)
SELECT count(*) AS rows_in_staging FROM iris_staging.portfolio_audit_staging;

-- 2. Content check
SELECT property_id, task_id, as_of_date, annual_ppa_revenue_eur,
       walt_years, effective_ppa_term_years, geometry_crs
FROM iris_staging.portfolio_audit_staging
ORDER BY property_id;

-- 3. Nothing was written outside iris_staging (expect only iris_staging)
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2;

-- 4. Privilege setup suggested for the candidate role (run by an administrator)
-- GRANT USAGE ON SCHEMA iris_staging TO iris_candidate;
-- GRANT SELECT, INSERT, UPDATE ON iris_staging.portfolio_audit_staging TO iris_candidate;
-- No grants on iris_core: the candidate role should have none.
