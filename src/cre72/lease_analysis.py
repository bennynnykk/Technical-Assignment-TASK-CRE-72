import numpy as np
import pandas as pd


DAYS_PER_YEAR = 365.25


def active_leases(leases, as_of):
    """Leases that are running on the as_of date (start <= as_of <= end).

    Leases that have not started yet or have already expired are excluded.
    Excluding future leases is the conservative choice for a PPA offtake base.
    """
    as_of = pd.Timestamp(as_of)

    start = pd.to_datetime(leases["start_date"])
    end = pd.to_datetime(leases["end_date"])

    active = leases[(start <= as_of) & (end >= as_of)].copy()
    active["end_date"] = pd.to_datetime(active["end_date"])
    active["remaining_years"] = (
        (active["end_date"] - as_of).dt.days / DAYS_PER_YEAR
    )

    return active


def lease_metrics(leases, as_of):
    """Per-property lease metrics as of a date.

    WALT (weighted average lease term) is the remaining lease term in years,
    weighted by annual rent, over active leases only.
    """
    active = active_leases(leases, as_of)

    columns = [
        "property_id",
        "active_lease_count",
        "active_annual_rent_eur",
        "walt_years",
    ]

    if active.empty:
        return pd.DataFrame(columns=columns)

    active["rent_x_years"] = (
        active["annual_rent_eur"] * active["remaining_years"]
    )

    grouped = active.groupby("property_id", as_index=False).agg(
        active_lease_count=("lease_id", "count"),
        active_annual_rent_eur=("annual_rent_eur", "sum"),
        rent_x_years=("rent_x_years", "sum"),
    )

    # A property whose active leases all have zero rent has no rent weighting.
    grouped["walt_years"] = np.where(
        grouped["active_annual_rent_eur"] > 0,
        grouped["rent_x_years"] / grouped["active_annual_rent_eur"],
        np.nan,
    )

    return grouped[columns]
