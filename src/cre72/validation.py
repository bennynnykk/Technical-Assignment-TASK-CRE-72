import logging

import pandas as pd
from shapely import wkt
from shapely.errors import ShapelyError
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid

from cre72.config import (
    EXPECTED_CRS,
    UTM32_EASTING_RANGE,
    UTM32_NORTHING_RANGE,
)


logger = logging.getLogger(__name__)

AREA_TOLERANCE = 0.01  # 1 % difference between stated and computed roof area


REQUIRED_COLUMNS = {
    "properties": {
        "property_id",
        "property_type",
        "building_area_m2",
        "land_area_m2",
    },
    "roofs": {
        "roof_id",
        "property_id",
        "roof_area_m2",
        "usable_roof_area_m2",
        "geometry_wkt",
        "crs",
    },
    "tenants": {
        "tenant_id",
        "property_id",
        "annual_demand_kwh",
    },
    "leases": {
        "lease_id",
        "tenant_id",
        "property_id",
        "start_date",
        "end_date",
        "annual_rent_eur",
    },
    "ppa_assumptions": {
        "property_id",
        "ppa_price_eur_per_kwh",
        "pv_density_kwp_per_m2",
        "annual_yield_kwh_per_kwp",
        "ppa_term_years",
    },
}


# --------------------------------------------------
# Dataset-level checks (structural problems stop the run)
# --------------------------------------------------

def validate_required_columns(df, dataset_name):
    missing = REQUIRED_COLUMNS[dataset_name] - set(df.columns)

    if missing:
        raise ValueError(
            f"{dataset_name}: missing columns: {sorted(missing)}"
        )


def validate_unique_keys(df, column, dataset_name):
    if df[column].isna().any():
        raise ValueError(
            f"{dataset_name}: {column} contains null values"
        )

    if df[column].duplicated().any():
        raise ValueError(
            f"{dataset_name}: duplicate values in {column}"
        )


def validate_numeric_range(df, column, minimum=0):
    values = pd.to_numeric(df[column], errors="coerce")

    if values.isna().any():
        raise ValueError(f"{column} contains non-numeric values")

    if (values < minimum).any():
        raise ValueError(f"{column} contains values below {minimum}")

    df[column] = values


def validate_foreign_keys(datasets):
    properties = datasets["properties"]
    roofs = datasets["roofs"]
    tenants = datasets["tenants"]
    leases = datasets["leases"]
    assumptions = datasets["ppa_assumptions"]

    property_ids = set(properties["property_id"])
    tenant_ids = set(tenants["tenant_id"])

    for name, df in [
        ("roofs", roofs),
        ("tenants", tenants),
        ("leases", leases),
        ("ppa_assumptions", assumptions),
    ]:
        unknown = set(df["property_id"]) - property_ids

        if unknown:
            raise ValueError(
                f"{name}: unknown property IDs: {sorted(unknown)}"
            )

    unknown_tenants = set(leases["tenant_id"]) - tenant_ids

    if unknown_tenants:
        raise ValueError(
            f"leases: unknown tenant IDs: {sorted(unknown_tenants)}"
        )

    tenant_property = tenants.set_index("tenant_id")["property_id"]

    for _, lease in leases.iterrows():
        if tenant_property[lease["tenant_id"]] != lease["property_id"]:
            raise ValueError(
                f"Lease {lease['lease_id']} has mismatched tenant/property"
            )


def validate_dates(leases):
    leases["start_date"] = pd.to_datetime(
        leases["start_date"], errors="coerce"
    )

    leases["end_date"] = pd.to_datetime(
        leases["end_date"], errors="coerce"
    )

    if leases["start_date"].isna().any():
        raise ValueError("Invalid lease start dates")

    if leases["end_date"].isna().any():
        raise ValueError("Invalid lease end dates")

    if (leases["end_date"] < leases["start_date"]).any():
        raise ValueError("Lease end date precedes start date")


def coordinates_in_utm32_range(easting, northing):
    return (
        UTM32_EASTING_RANGE[0] <= easting <= UTM32_EASTING_RANGE[1]
        and UTM32_NORTHING_RANGE[0] <= northing <= UTM32_NORTHING_RANGE[1]
    )


def validate_property_locations(properties):
    """Check CRS label and coordinate plausibility of property points."""
    if "crs" in properties.columns:
        wrong = properties[properties["crs"] != EXPECTED_CRS]

        if not wrong.empty:
            raise ValueError(
                f"properties: unexpected CRS for {wrong['property_id'].tolist()}"
            )

    if {"easting_m", "northing_m"} <= set(properties.columns):
        for _, row in properties.iterrows():
            easting = pd.to_numeric(row["easting_m"], errors="coerce")
            northing = pd.to_numeric(row["northing_m"], errors="coerce")

            if pd.isna(easting) or pd.isna(northing) or not (
                coordinates_in_utm32_range(easting, northing)
            ):
                raise ValueError(
                    f"properties: {row['property_id']} coordinates are missing "
                    f"or outside the {EXPECTED_CRS} plausibility window"
                )


# --------------------------------------------------
# Row-level roof checks (bad rows are quarantined, not fatal)
# --------------------------------------------------

def _polygonal_part(geometry):
    """Keep only polygon parts of a repaired geometry (make_valid may
    return a GeometryCollection that also contains lines or points)."""
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry

    parts = [
        part
        for part in getattr(geometry, "geoms", [])
        if isinstance(part, (Polygon, MultiPolygon)) and not part.is_empty
    ]

    if not parts:
        return None

    return unary_union(parts)


def check_roof_row(row):
    """Validate one roof row.

    Returns (clean_wkt, computed_area_m2, was_repaired, rejection_reason).
    rejection_reason is None when the row is accepted.
    """
    roof_id = row["roof_id"]

    if row["crs"] != EXPECTED_CRS:
        return None, None, False, f"unexpected CRS {row['crs']}"

    if row["usable_roof_area_m2"] > row["roof_area_m2"]:
        return None, None, False, "usable roof area exceeds total roof area"

    if row["roof_area_m2"] <= 0:
        return None, None, False, "roof_area_m2 must be greater than zero"

    raw = row["geometry_wkt"]

    if not isinstance(raw, str) or not raw.strip():
        return None, None, False, "missing geometry"

    try:
        geometry = wkt.loads(raw)
    except (ShapelyError, ValueError) as error:
        return None, None, False, f"unparseable WKT ({error})"

    if geometry.is_empty:
        return None, None, False, "empty geometry"

    repaired = False

    if not geometry.is_valid:
        geometry = make_valid(geometry)
        repaired = True

    geometry = _polygonal_part(geometry)

    if geometry is None or geometry.is_empty or not geometry.is_valid:
        return None, None, repaired, "geometry could not be repaired to a polygon"

    min_x, min_y, max_x, max_y = geometry.bounds

    if not (
        coordinates_in_utm32_range(min_x, min_y)
        and coordinates_in_utm32_range(max_x, max_y)
    ):
        return (
            None,
            None,
            repaired,
            f"coordinates outside the {EXPECTED_CRS} plausibility window",
        )

    area = geometry.area

    if area <= 0:
        return None, None, repaired, "geometry area is zero"

    if abs(area - row["roof_area_m2"]) / row["roof_area_m2"] > AREA_TOLERANCE:
        return (
            None,
            None,
            repaired,
            f"geometry area {area:.1f} m2 differs from roof_area_m2 "
            f"{row['roof_area_m2']} by more than {AREA_TOLERANCE:.0%}",
        )

    logger.debug("Roof %s accepted (repaired=%s)", roof_id, repaired)

    return geometry.wkt, area, repaired, None


def validate_roofs(roofs):
    """Return (valid_roofs, rejected_roofs, repaired_count)."""
    accepted_rows = []
    rejected_rows = []
    repaired_count = 0

    for _, row in roofs.iterrows():
        clean_wkt, area, repaired, reason = check_roof_row(row)

        if repaired:
            repaired_count += 1

        if reason is not None:
            logger.warning("Roof %s rejected: %s", row["roof_id"], reason)

            rejected = row.to_dict()
            rejected["rejection_reason"] = reason
            rejected_rows.append(rejected)
            continue

        accepted = row.to_dict()
        accepted["geometry_wkt"] = clean_wkt
        accepted["geometry_area_m2"] = round(area, 2)
        accepted["geometry_repaired"] = repaired
        accepted_rows.append(accepted)

    valid = pd.DataFrame(accepted_rows, columns=list(roofs.columns) + [
        "geometry_area_m2",
        "geometry_repaired",
    ])
    rejected = pd.DataFrame(
        rejected_rows, columns=list(roofs.columns) + ["rejection_reason"]
    )

    return valid, rejected, repaired_count


# --------------------------------------------------
# Orchestration
# --------------------------------------------------

def validate_datasets(datasets):
    report = {
        "status": "success",
        "datasets": {},
        "repaired_geometries": 0,
        "roofs_rejected": [],
        "properties_without_valid_roof": [],
    }

    for name, df in datasets.items():
        validate_required_columns(df, name)

        report["datasets"][name] = {
            "rows_in": len(df),
            "missing_values": int(df.isna().sum().sum()),
        }

    validate_unique_keys(
        datasets["properties"], "property_id", "properties"
    )
    validate_unique_keys(
        datasets["roofs"], "roof_id", "roofs"
    )
    validate_unique_keys(
        datasets["tenants"], "tenant_id", "tenants"
    )
    validate_unique_keys(
        datasets["leases"], "lease_id", "leases"
    )
    validate_unique_keys(
        datasets["ppa_assumptions"], "property_id", "ppa_assumptions"
    )

    numeric_columns = {
        "properties": ["building_area_m2", "land_area_m2"],
        "roofs": ["roof_area_m2", "usable_roof_area_m2"],
        "tenants": ["annual_demand_kwh"],
        "leases": ["annual_rent_eur"],
        "ppa_assumptions": [
            "ppa_price_eur_per_kwh",
            "pv_density_kwp_per_m2",
            "annual_yield_kwh_per_kwp",
            "ppa_term_years",
        ],
    }

    for dataset_name, columns in numeric_columns.items():
        for column in columns:
            validate_numeric_range(
                datasets[dataset_name], column
            )

    assumptions = datasets["ppa_assumptions"]

    if (assumptions["ppa_price_eur_per_kwh"] <= 0).any():
        raise ValueError("PPA prices must be greater than zero")

    if (assumptions["pv_density_kwp_per_m2"] <= 0).any():
        raise ValueError("PV density must be greater than zero")

    if (assumptions["annual_yield_kwh_per_kwp"] <= 0).any():
        raise ValueError("Annual yield must be greater than zero")

    if (assumptions["ppa_term_years"] <= 0).any():
        raise ValueError("PPA term must be greater than zero")

    validate_property_locations(datasets["properties"])
    validate_foreign_keys(datasets)
    validate_dates(datasets["leases"])

    valid_roofs, rejected_roofs, repaired_count = validate_roofs(
        datasets["roofs"]
    )

    datasets["roofs"] = valid_roofs
    datasets["roofs_rejected"] = rejected_roofs

    for name in REQUIRED_COLUMNS:
        rows_in = report["datasets"][name]["rows_in"]
        rows_valid = len(datasets[name])
        report["datasets"][name]["rows_valid"] = rows_valid
        report["datasets"][name]["rows_rejected"] = rows_in - rows_valid

    report["repaired_geometries"] = repaired_count
    report["roofs_rejected"] = [
        {"roof_id": row["roof_id"], "reason": row["rejection_reason"]}
        for _, row in rejected_roofs.iterrows()
    ]

    covered = set(valid_roofs["property_id"])
    missing = sorted(set(datasets["properties"]["property_id"]) - covered)
    report["properties_without_valid_roof"] = missing

    if missing:
        logger.warning(
            "Properties without a valid roof (excluded from PV results): %s",
            missing,
        )

    logger.info(
        "Validation finished: roofs in=%d valid=%d rejected=%d repaired=%d",
        len(datasets["roofs"]) + len(rejected_roofs),
        len(valid_roofs),
        len(rejected_roofs),
        repaired_count,
    )

    return datasets, report
