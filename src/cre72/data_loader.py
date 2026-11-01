import logging
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

DATASET_FILES = {
    "properties": "properties.csv",
    "roofs": "roofs.csv",
    "tenants": "tenants.csv",
    "leases": "leases.csv",
    "ppa_assumptions": "ppa_assumptions.csv",
}


def load_datasets(data_dir=None):
    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR

    datasets = {}

    for name, filename in DATASET_FILES.items():
        path = data_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

        try:
            datasets[name] = pd.read_csv(path)
        except pd.errors.EmptyDataError as error:
            raise ValueError(f"{name}: file is empty: {path}") from error

        logger.info("Loaded %s: %d rows from %s", name, len(datasets[name]), path)

    return datasets
