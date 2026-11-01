"""Upsert data/processed/ppa_results.csv into iris_staging.portfolio_audit_staging.

Requires DB_URI. Run scripts/run_pipeline.py first.
Only the staging table is ever touched; the target is hard-coded in cre72.database.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cre72.database import upsert_results  # noqa: E402
from cre72.logging_config import setup_logging  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_FILE = PROJECT_ROOT / "data" / "processed" / "ppa_results.csv"

logger = logging.getLogger("write_to_database")


def main():
    setup_logging()

    if not RESULT_FILE.exists():
        logger.error("%s not found. Run scripts/run_pipeline.py first.", RESULT_FILE)
        sys.exit(2)

    results = pd.read_csv(RESULT_FILE)

    counts = upsert_results(results)

    print(counts)

    if counts["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
