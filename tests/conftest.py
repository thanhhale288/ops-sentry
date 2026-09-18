import pytest

from app.rag.retrieve import ingest, reset_client
from app.store import init_db


@pytest.fixture(scope="session", autouse=True)
def boot() -> None:
    reset_client()
    init_db()
    ingest(force=True)
