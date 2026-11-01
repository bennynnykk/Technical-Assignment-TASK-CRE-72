import os
from datetime import date

from dotenv import load_dotenv


load_dotenv()

# Fixed default so repeated runs give identical results (idempotency).
DEFAULT_AS_OF_DATE = "2026-11-01"

EXPECTED_CRS = "EPSG:25832"

# Rough validity window of ETRS89 / UTM zone 32N for Europe.
# Used only as a plausibility check on coordinates; it does not
# prove that a coordinate is really in the claimed CRS.
UTM32_EASTING_RANGE = (166_000.0, 834_000.0)
UTM32_NORTHING_RANGE = (4_200_000.0, 9_400_000.0)


def get_database_uri():
    database_uri = os.getenv("DB_URI")

    if not database_uri:
        raise RuntimeError("DB_URI is not configured")

    return database_uri


def get_as_of_date():
    value = os.getenv("AS_OF_DATE", DEFAULT_AS_OF_DATE)

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(
            f"AS_OF_DATE must be an ISO date (YYYY-MM-DD), got: {value!r}"
        ) from error
