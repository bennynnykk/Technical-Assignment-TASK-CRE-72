"""Database tests.

Unit tests need no database. The integration tests run only when TEST_DB_URI points to a
DISPOSABLE PostgreSQL database whose name contains "test" (guard against shared databases).
They create iris_staging.portfolio_audit_staging from sql/01_staging_ddl.sql, drop it again
at the start, and never touch any other schema.

    TEST_DB_URI=postgresql+psycopg://user:pw@localhost:5432/iris_test pytest -m integration
"""

import os
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import Column, MetaData, Numeric, Table, Text, create_engine, text

from cre72 import database
from cre72.database import prepare_records, upsert_results
from cre72.pipeline import run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DDL_FILE = PROJECT_ROOT / "sql" / "01_staging_ddl.sql"
AS_OF = date(2026, 11, 1)


def _fake_target(primary_key="property_id"):
    metadata = MetaData()

    return Table(
        "portfolio_audit_staging",
        metadata,
        Column("property_id", Text, primary_key=(primary_key == "property_id")),
        Column("annual_ppa_revenue_eur", Numeric),
        Column("other_key", Text, primary_key=(primary_key == "other_key")),
        schema="iris_staging",
    )


def test_target_is_hard_coded_to_staging():
    assert database.TARGET_SCHEMA == "iris_staging"
    assert database.TARGET_TABLE == "portfolio_audit_staging"


def test_unknown_columns_are_refused():
    frame = pd.DataFrame([{"property_id": "P1", "surprise": 1}])

    with pytest.raises(RuntimeError, match="not present in target table"):
        prepare_records(frame, _fake_target())


def test_duplicate_keys_are_refused():
    frame = pd.DataFrame([
        {"property_id": "P1", "annual_ppa_revenue_eur": 1},
        {"property_id": "P1", "annual_ppa_revenue_eur": 2},
    ])

    with pytest.raises(ValueError, match="Duplicate primary keys"):
        prepare_records(frame, _fake_target())


def test_null_keys_are_refused():
    frame = pd.DataFrame([{"property_id": None, "annual_ppa_revenue_eur": 1}])

    with pytest.raises(ValueError, match="null"):
        prepare_records(frame, _fake_target())


def test_table_without_property_id_key_is_refused():
    frame = pd.DataFrame([{"property_id": "P1", "other_key": "x"}])

    with pytest.raises(RuntimeError, match="primary key"):
        prepare_records(frame, _fake_target(primary_key="other_key"))


def test_nan_becomes_none():
    frame = pd.DataFrame([
        {"property_id": "P1", "annual_ppa_revenue_eur": float("nan")}
    ])

    records, _ = prepare_records(frame, _fake_target())

    assert records[0]["annual_ppa_revenue_eur"] is None


# --------------------------------------------------
# Integration tests (disposable PostgreSQL only)
# --------------------------------------------------

TEST_DB_URI = os.getenv("TEST_DB_URI")

needs_db = pytest.mark.skipif(
    not TEST_DB_URI, reason="TEST_DB_URI not set (integration test)"
)


@pytest.fixture
def engine():
    engine = create_engine(TEST_DB_URI)

    database_name = engine.url.database or ""

    if "test" not in database_name:
        engine.dispose()
        pytest.fail(
            f"Refusing to run: database name {database_name!r} must contain 'test'"
        )

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS iris_staging CASCADE"))
        connection.execute(text(DDL_FILE.read_text(encoding="utf-8")))

    yield engine

    engine.dispose()


@pytest.fixture
def results(sample_data_dir, tmp_path):
    _, frame = run_pipeline(
        data_dir=sample_data_dir, output_dir=tmp_path, as_of=AS_OF
    )
    return frame


def _count(engine):
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM iris_staging.portfolio_audit_staging")
        ).scalar_one()


@needs_db
@pytest.mark.integration
def test_first_load_inserts_all_rows(engine, results):
    counts = upsert_results(results, engine=engine)

    assert counts == {"processed": 3, "inserted": 3, "updated": 0, "failed": 0}
    assert _count(engine) == 3


@needs_db
@pytest.mark.integration
def test_second_load_is_idempotent(engine, results):
    upsert_results(results, engine=engine)
    counts = upsert_results(results, engine=engine)

    assert counts == {"processed": 3, "inserted": 0, "updated": 3, "failed": 0}
    assert _count(engine) == 3


@needs_db
@pytest.mark.integration
def test_changed_value_updates_in_place(engine, results):
    upsert_results(results, engine=engine)

    changed = results.copy()
    changed.loc[changed["property_id"] == "PROP-001", "annual_ppa_revenue_eur"] = 1.0

    counts = upsert_results(changed, engine=engine)

    with engine.connect() as connection:
        value = connection.execute(
            text(
                "SELECT annual_ppa_revenue_eur FROM iris_staging.portfolio_audit_staging "
                "WHERE property_id = 'PROP-001'"
            )
        ).scalar_one()

    assert counts["updated"] == 3
    assert float(value) == 1.0
    assert _count(engine) == 3


@needs_db
@pytest.mark.integration
def test_only_staging_schema_is_populated(engine, results):
    upsert_results(results, engine=engine)

    with engine.connect() as connection:
        schemas = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT DISTINCT table_schema FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'public')"
                )
            )
        }

    assert schemas == {"iris_staging"}


@needs_db
@pytest.mark.integration
def test_failed_batch_is_counted_and_nothing_is_written(engine, results):
    broken = results.copy()
    broken["geometry_crs"] = "EPSG:4326"  # violates the EPSG:25832 CHECK constraint

    counts = upsert_results(broken, engine=engine)

    assert counts == {"processed": 3, "inserted": 0, "updated": 0, "failed": 3}
    assert _count(engine) == 0


@needs_db
@pytest.mark.integration
def test_missing_table_is_reported_not_created(engine, results):
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE iris_staging.portfolio_audit_staging"))

    with pytest.raises(RuntimeError, match="does not exist"):
        upsert_results(results, engine=engine)
