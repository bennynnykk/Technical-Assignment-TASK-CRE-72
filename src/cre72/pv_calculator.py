import pandas as pd
from shapely import wkt
from shapely.ops import unary_union

from cre72.config import EXPECTED_CRS


def _union_wkt(values):
    geometries = [wkt.loads(value) for value in values if isinstance(value, str)]

    if not geometries:
        return None

    return unary_union(geometries).wkt


def calculate_pv_potential(roofs, assumptions):
    merged = roofs.merge(
        assumptions,
        on="property_id",
        how="inner",
        validate="many_to_one",
    )

    if merged.empty:
        raise ValueError("No matching roofs and PPA assumptions")

    merged["pv_capacity_kwp"] = (
        merged["usable_roof_area_m2"]
        * merged["pv_density_kwp_per_m2"]
    )

    merged["annual_generation_kwh"] = (
        merged["pv_capacity_kwp"]
        * merged["annual_yield_kwh_per_kwp"]
    )

    results = (
        merged.groupby("property_id", as_index=False)
        .agg(
            roof_count=("roof_id", "count")
            if "roof_id" in merged.columns
            else ("usable_roof_area_m2", "count"),
            usable_roof_area_m2=("usable_roof_area_m2", "sum"),
            pv_capacity_kwp=("pv_capacity_kwp", "sum"),
            annual_generation_kwh=(
                "annual_generation_kwh", "sum"
            ),
        )
    )

    # Keep the validated roof outline (EPSG:25832) for provenance.
    if "geometry_wkt" in merged.columns:
        outlines = (
            merged.groupby("property_id")["geometry_wkt"]
            .apply(_union_wkt)
            .rename("roof_geometry_wkt")
            .reset_index()
        )
        results = results.merge(outlines, on="property_id", how="left")
        results["geometry_crs"] = EXPECTED_CRS

    return results
