import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app as fastapi_app

TEST_DB_NAME = "appdb_test"
_base_url = make_url(settings.database_url)
_test_url = _base_url.set(database=TEST_DB_NAME)
_maintenance_url = _base_url.set(database="postgres")

test_engine = create_engine(_test_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def _ensure_test_database() -> None:
    maintenance_engine = create_engine(_maintenance_url, isolation_level="AUTOCOMMIT")
    with maintenance_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.exec_driver_sql(f'CREATE DATABASE "{TEST_DB_NAME}"')
    maintenance_engine.dispose()


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    _ensure_test_database()
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    return TestClient(fastapi_app)
