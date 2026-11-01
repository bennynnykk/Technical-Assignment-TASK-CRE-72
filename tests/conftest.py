from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_data_dir():
    return PROJECT_ROOT / "data" / "raw"


@pytest.fixture
def defective_data_dir():
    return PROJECT_ROOT / "tests" / "fixtures" / "defective"
