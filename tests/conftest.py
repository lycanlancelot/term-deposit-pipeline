from pathlib import Path

import pytest

from term_deposit.data import add_campaign_date, load_raw

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "dataset.csv"


@pytest.fixture(scope="session")
def raw() -> "pd.DataFrame":  # noqa: F821
    return load_raw(DATA_PATH)


@pytest.fixture(scope="session")
def dated(raw) -> "pd.DataFrame":  # noqa: F821
    return add_campaign_date(raw)
