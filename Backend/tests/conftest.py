"""Pytest test configuration and fixtures for RailSync 2.0.

Provides an in-memory SQLite database with JSONB compatibility,
seeded with test corridor segments, and overrides FastAPI's get_db dependency.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

# Add Backend and workspace root (RailSync) to sys.path
_backend_dir = Path(__file__).resolve().parent.parent
_repo_root = _backend_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_db
from app.db.models import Base, Segment, MaintenanceTask, RiskPrediction
from app.main import app



# Compile Postgres JSONB as TEXT in SQLite for testing
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # Enable SQLite foreign key constraints
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Returns a fresh transactional session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionTesting = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionTesting()

    # Pre-seed a test segment
    test_seg = Segment(
        segment_id="SEG-TEST-001",
        division="Delhi",
        section="Delhi-Ghaziabad",
        corridor="Delhi-Howrah",
        asset_type="TRACK",
        length_km=12.5,
        age_years=15.0,
        installation_year=2011,
        curve_gradient_class="gentle",
        monsoon_exposure="medium",
        freight_density_class="high",
    )
    session.add(test_seg)

    test_seg2 = Segment(
        segment_id="SEG-TEST-002",
        division="Mumbai",
        section="Mumbai-Kalyan",
        corridor="Delhi-Mumbai",
        asset_type="OHE",
        length_km=8.0,
        age_years=25.0,
        installation_year=2001,
        curve_gradient_class="moderate",
        monsoon_exposure="high",
        freight_density_class="very_high",
    )
    session.add(test_seg2)
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
