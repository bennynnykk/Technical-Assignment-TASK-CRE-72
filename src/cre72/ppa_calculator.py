import logging

import numpy as np
import pandas as pd

from cre72.lease_analysis import active_leases, lease_metrics


logger = logging.getLogger(__name__)


def calculate_ppa_revenue(
    pv_results,
    tenants,
    assumptions,
    leases=None,
    as_of=None,
):
    """Annual onsite PPA volume and revenue per property.

    Without leases: all tenants count and the nominal PPA term is used.
    With leases (and an as_of date): only tenants with an active lease count
    as offtakers, the PPA term is capped by the rent-weighted lease term
    (WALT), and a status quo vs PV+PPA comparison is added.

    All values are annual aggregates; there is no hourly matching, discounting,
    CAPEX or OPEX. Revenue is gross.
    """
    if leases is not None and as_of is None:
        raise ValueError("as_of is required when leases are provided")

    offtake_tenants = tenants

    if leases is not None:
        active = active_leases(leases, as_of)
        offtake_tenants = tenants[tenants["tenant_id"].isin(active["tenant_id"])]

        excluded = len(tenants) - len(offtake_tenants)

        if excluded:
            logger.warning(
                "%d tenant(s) without an active lease on %s excluded from "
                "PPA demand",
                excluded,
                pd.Timestamp(as_of).date(),
            )

    tenant_demand = (
        offtake_tenants.groupby("property_id", as_index=False)
        .agg(
            total_tenant_demand_kwh=(
                "annual_demand_kwh", "sum"
            )
        )
    )

    results = (
        pv_results
        .merge(
            tenant_demand,
            on="property_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            assumptions[
                [
                    "property_id",
                    "ppa_price_eur_per_kwh",
                    "ppa_term_years",
                ]
            ],
            on="property_id",
            how="inner",
            validate="one_to_one",
        )
    )

    results["total_tenant_demand_kwh"] = (
        results["total_tenant_demand_kwh"].fillna(0)
    )

    results["ppa_volume_kwh"] = results[
        [
            "annual_generation_kwh",
            "total_tenant_demand_kwh",
        ]
    ].min(axis=1)

    results["surplus_energy_kwh"] = (
        results["annual_generation_kwh"]
        - results["ppa_volume_kwh"]
    ).clip(lower=0)

    results["uncovered_tenant_demand_kwh"] = (
        results["total_tenant_demand_kwh"]
        - results["ppa_volume_kwh"]
    ).clip(lower=0)

    results["tenant_demand_coverage_ratio"] = np.where(
        results["total_tenant_demand_kwh"] > 0,
        results["ppa_volume_kwh"]
        / results["total_tenant_demand_kwh"].where(
            results["total_tenant_demand_kwh"] > 0
        ),
        np.nan,
    )

    results["annual_ppa_revenue_eur"] = (
        results["ppa_volume_kwh"]
        * results["ppa_price_eur_per_kwh"]
    )

    # Revenue if the nominal PPA term were contractually secured.
    results["nominal_contract_revenue_eur"] = (
        results["annual_ppa_revenue_eur"]
        * results["ppa_term_years"]
    )

    if leases is None:
        return results

    metrics = lease_metrics(leases, as_of)

    results = results.merge(metrics, on="property_id", how="left")

    results["active_lease_count"] = (
        results["active_lease_count"].fillna(0).astype(int)
    )
    results["active_annual_rent_eur"] = (
        results["active_annual_rent_eur"].fillna(0.0)
    )

    # Offtake cannot reliably exceed the remaining lease term: cap it.
    results["effective_ppa_term_years"] = np.minimum(
        results["ppa_term_years"],
        results["walt_years"].fillna(0.0),
    ).round(2)

    results["lease_capped_contract_revenue_eur"] = (
        results["annual_ppa_revenue_eur"]
        * results["effective_ppa_term_years"]
    )

    # Status quo = rent only. Optimized = rent + gross PV/PPA revenue.
    results["status_quo_annual_income_eur"] = results["active_annual_rent_eur"]

    results["optimized_annual_gross_income_eur"] = (
        results["active_annual_rent_eur"]
        + results["annual_ppa_revenue_eur"]
    )

    results["annual_income_uplift_pct"] = np.where(
        results["active_annual_rent_eur"] > 0,
        results["annual_ppa_revenue_eur"]
        / results["active_annual_rent_eur"].where(
            results["active_annual_rent_eur"] > 0
        )
        * 100,
        np.nan,
    )

    results["walt_years"] = results["walt_years"].round(2)

    return results
