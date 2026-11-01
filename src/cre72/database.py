import logging

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, inspect, literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from cre72.config import get_database_uri


logger = logging.getLogger(__name__)

# The only place this project is allowed to write to. Hard-coded on purpose:
# it must never come from user input or configuration.
TARGET_SCHEMA = "iris_staging"
TARGET_TABLE = "portfolio_audit_staging"

KEY_COLUMN = "property_id"
BATCH_SIZE = 500
STATEMENT_TIMEOUT_MS = 30_000


def create_db_engine():
    return create_engine(
        get_database_uri(),
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 10,
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
        },
    )


def get_target_table(engine):
    """Reflect the target table. Never creates or alters anything."""
    inspector = inspect(engine)

    if TARGET_SCHEMA not in inspector.get_schema_names():
        raise RuntimeError(
            f"Target schema does not exist: {TARGET_SCHEMA}"
        )

    if not inspector.has_table(TARGET_TABLE, schema=TARGET_SCHEMA):
        raise RuntimeError(
            f"Target table does not exist: {TARGET_SCHEMA}.{TARGET_TABLE}. "
            "Confirm the target DDL with Tariq before writing."
        )

    return Table(
        TARGET_TABLE,
        MetaData(),
        schema=TARGET_SCHEMA,
        autoload_with=engine,
    )


def prepare_records(results, target):
    """Validate the result frame against the target table and return
    a list of plain-Python records (NaN converted to None)."""
    primary_keys = [column.name for column in target.primary_key.columns]

    if not primary_keys:
        raise RuntimeError(
            "Target table has no primary key; safe upsert is impossible"
        )

    if KEY_COLUMN not in primary_keys:
        raise RuntimeError(
            f"Expected {KEY_COLUMN} to be part of the primary key. "
            "Confirm the actual target DDL before proceeding."
        )

    unknown_columns = set(results.columns) - set(target.columns.keys())

    if unknown_columns:
        raise RuntimeError(
            "Input contains columns not present in target table: "
            f"{sorted(unknown_columns)}"
        )

    missing_keys = set(primary_keys) - set(results.columns)

    if missing_keys:
        raise RuntimeError(f"Missing primary key columns: {sorted(missing_keys)}")

    if results[primary_keys].isna().any().any():
        raise ValueError("Primary key columns contain null values")

    if results.duplicated(subset=primary_keys).any():
        raise ValueError(
            f"Duplicate primary keys in input ({primary_keys}); "
            "refusing to write"
        )

    frame = results.copy()

    if "as_of_date" in frame.columns:
        frame["as_of_date"] = pd.to_datetime(frame["as_of_date"]).dt.date

    frame = frame.astype(object).where(frame.notna(), None)

    return frame.to_dict(orient="records"), primary_keys


def upsert_results(results, engine=None):
    """Idempotent upsert into iris_staging.portfolio_audit_staging.

    Returns a dict with processed / inserted / updated / failed counts.
    Running it twice with the same input inserts nothing the second time.
    """
    own_engine = engine is None
    engine = engine or create_db_engine()

    try:
        target = get_target_table(engine)
        records, primary_keys = prepare_records(results, target)

        counts = {
            "processed": len(records),
            "inserted": 0,
            "updated": 0,
            "failed": 0,
        }

        if not records:
            logger.info("No records to write")
            return counts

        input_columns = set(results.columns)

        update_columns = {
            name: getattr(insert(target).excluded, name)
            for name in target.columns.keys()
            if name in input_columns and name not in primary_keys
        }

        if "updated_at" in target.columns and "updated_at" not in input_columns:
            update_columns["updated_at"] = literal_column("now()")

        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start:start + BATCH_SIZE]

            statement = insert(target).values(batch)

            if update_columns:
                statement = statement.on_conflict_do_update(
                    index_elements=primary_keys,
                    set_=update_columns,
                )
            else:
                statement = statement.on_conflict_do_nothing(
                    index_elements=primary_keys
                )

            # xmax = 0 is true for freshly inserted rows, false for updated ones.
            statement = statement.returning(
                literal_column("(xmax = 0)").label("was_inserted")
            )

            try:
                with engine.begin() as connection:
                    rows = connection.execute(statement).fetchall()
            except SQLAlchemyError as error:
                counts["failed"] += len(batch)
                logger.error(
                    "Batch starting at record %d failed (%d records): %s",
                    start,
                    len(batch),
                    error.__class__.__name__,
                )
                logger.debug("Batch failure detail: %s", error)
                continue

            inserted = sum(1 for row in rows if row.was_inserted)
            counts["inserted"] += inserted
            counts["updated"] += len(rows) - inserted

        logger.info(
            "Database upsert into %s.%s: processed=%d inserted=%d updated=%d failed=%d",
            TARGET_SCHEMA,
            TARGET_TABLE,
            counts["processed"],
            counts["inserted"],
            counts["updated"],
            counts["failed"],
        )

        return counts
    finally:
        if own_engine:
            engine.dispose()
