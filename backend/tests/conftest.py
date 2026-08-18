from __future__ import annotations

import os

os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("AUTO_INGEST_ON_STARTUP", "false")
os.environ.setdefault("ADMIN_API_ENABLED", "true")
os.environ.setdefault("EXCHANGE_PROVIDER", "mock")
os.environ.setdefault("NEWS_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ALLOW_MOCK_FALLBACK", "true")

from app.config import get_settings

get_settings.cache_clear()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.main import app
from app.models import CollectionStatus, Event, Forecast, Indicator, Observation  # noqa: F401
from app.services.catalog import seed_indicators


@pytest.fixture
def db_engine(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    seed_indicators(session)
    session.close()
    yield engine, factory
    engine.dispose()


@pytest.fixture
def db(db_engine) -> Session:
    engine, factory = db_engine
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_engine):
    engine, factory = db_engine

    def _override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
