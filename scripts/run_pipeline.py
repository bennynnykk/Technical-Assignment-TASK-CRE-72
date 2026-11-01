"""Run the full TASK-CRE-72 pipeline: validate -> PV -> PPA (-> optional staging write).

Examples:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --data-dir tests/fixtures/defective --output-dir /tmp/out
    DB_URI=... python scripts/run_pipeline.py --write-db
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cre72.logging_config import setup_logging  # noqa: E402
from cre72.pipeline import run_pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="folder with the five input CSV files")
    parser.add_argument("--output-dir", help="folder for outputs (default data/processed)")
    parser.add_argument("--as-of", help="valuation date, YYYY-MM-DD (default 2026-11-01)")
    parser.add_argument(
        "--write-db",
        action="store_true",
        help="upsert results into iris_staging.portfolio_audit_staging (needs DB_URI)",
    )
    args = parser.parse_args()

    setup_logging()

    as_of = date.fromisoformat(args.as_of) if args.as_of else None

    summary, results = run_pipeline(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        as_of=as_of,
        write_db=args.write_db,
    )

    print(results[[
        "property_id",
        "annual_generation_kwh",
        "ppa_volume_kwh",
        "annual_ppa_revenue_eur",
        "walt_years",
        "effective_ppa_term_years",
        "lease_capped_contract_revenue_eur",
    ]].to_string(index=False))

    if summary["db"] and summary["db"]["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
