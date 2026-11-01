import json
import logging
from pathlib import Path

from cre72 import TASK_ID
from cre72.config import get_as_of_date
from cre72.data_loader import load_datasets
from cre72.pv_calculator import calculate_pv_potential
from cre72.ppa_calculator import calculate_ppa_revenue
from cre72.validation import validate_datasets


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

# Columns written to ppa_results.csv and (optionally) to the staging table.
# Order is fixed so outputs are reproducible and match sql/01_staging_ddl.sql.
RESULT_COLUMNS = [
    "property_id",
    "task_id",
    "as_of_date",
    "data_source",
    "roof_count",
    "usable_roof_area_m2",
    "pv_capacity_kwp",
    "annual_generation_kwh",
    "total_tenant_demand_kwh",
    "ppa_price_eur_per_kwh",
    "ppa_term_years",
    "ppa_volume_kwh",
    "surplus_energy_kwh",
    "uncovered_tenant_demand_kwh",
    "tenant_demand_coverage_ratio",
    "annual_ppa_revenue_eur",
    "nominal_contract_revenue_eur",
    "active_lease_count",
    "active_annual_rent_eur",
    "walt_years",
    "effective_ppa_term_years",
    "lease_capped_contract_revenue_eur",
    "status_quo_annual_income_eur",
    "optimized_annual_gross_income_eur",
    "annual_income_uplift_pct",
    "roof_geometry_wkt",
    "geometry_crs",
]


def _round_results(results):
    rounded = results.copy()

    for column in rounded.columns:
        if rounded[column].dtype.kind == "f":
            rounded[column] = rounded[column].round(4)

    return rounded


def run_pipeline(data_dir=None, output_dir=None, as_of=None, write_db=False):
    """Validate -> PV potential -> PPA revenue (-> optional staging upsert).

    Returns a summary dict with the counts that were also logged.
    """
    output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    as_of = as_of or get_as_of_date()

    logger.info("Starting %s, as_of=%s", TASK_ID, as_of)

    datasets = load_datasets(data_dir)
    raw_property_count = len(datasets["properties"])

    datasets, report = validate_datasets(datasets)

    for name, frame in datasets.items():
        filename = (
            "roofs_rejected.csv"
            if name == "roofs_rejected"
            else f"{name}_validated.csv"
        )
        frame.to_csv(output_dir / filename, index=False)

    with open(output_dir / "validation_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    pv_results = calculate_pv_potential(
        datasets["roofs"], datasets["ppa_assumptions"]
    )
    pv_results.to_csv(output_dir / "pv_results.csv", index=False)

    results = calculate_ppa_revenue(
        pv_results,
        datasets["tenants"],
        datasets["ppa_assumptions"],
        leases=datasets["leases"],
        as_of=as_of,
    )

    sources = (
        datasets["properties"].set_index("property_id")["data_source"]
        if "data_source" in datasets["properties"].columns
        else None
    )

    results["task_id"] = TASK_ID
    results["as_of_date"] = as_of.isoformat()
    results["data_source"] = (
        results["property_id"].map(sources) if sources is not None else "unknown"
    )

    results = _round_results(results[RESULT_COLUMNS])
    results.to_csv(output_dir / "ppa_results.csv", index=False)

    summary = {
        "task_id": TASK_ID,
        "as_of_date": as_of.isoformat(),
        "properties_in": raw_property_count,
        "properties_with_results": len(results),
        "roofs_rejected": len(report["roofs_rejected"]),
        "geometries_repaired": report["repaired_geometries"],
        "db": None,
    }

    if write_db:
        from cre72.database import upsert_results

        summary["db"] = upsert_results(results)

    with open(output_dir / "run_summary.json", "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    logger.info("Pipeline finished: %s", summary)

    return summary, results
