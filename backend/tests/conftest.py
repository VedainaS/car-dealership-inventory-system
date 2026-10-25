import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

# Import-time engine URL only; each test uses its own file via the db_engine fixture.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-pytest-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "30")

from app.database import Base, get_db
import app.database as database_module
from app.main import app


@pytest.fixture()
def db_engine(tmp_path: Path):
    db_file = tmp_path / "test.db"
    database_url = f"sqlite:///{db_file.as_posix()}"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if database_module.engine is not engine:
        database_module.engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine) -> Generator[TestClient, None, None]:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    original_engine = database_module.engine
    original_session_local = database_module.SessionLocal

    database_module.engine = db_engine
    database_module.SessionLocal = TestingSessionLocal

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    database_module.engine = original_engine
    database_module.SessionLocal = original_session_local


# ---------------------------------------------------------------------------
# Concurrent-purchase fixtures
#
# The standard db_engine uses StaticPool, which funnels every session through
# a single underlying SQLite connection.  That is ideal for isolation in unit
# tests, but it prevents the concurrency test from exercising two independent
# transactions simultaneously.
#
# concurrent_db_engine uses NullPool so that every session.begin() opens its
# own SQLite connection.  WAL journal mode is enabled so a second writer can
# attempt its transaction while the first is still in flight (SQLite still
# serialises commits, but WAL avoids the exclusive-lock phase that would
# otherwise prevent the second connection from even starting a write).
# ---------------------------------------------------------------------------


@pytest.fixture()
def concurrent_db_engine(tmp_path: Path):
    """NullPool + WAL engine – each DB session gets an independent connection."""
    db_file = tmp_path / "concurrent.db"
    database_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False, "timeout": 10},
        poolclass=NullPool,
    )
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def concurrent_db_session(concurrent_db_engine) -> Generator[Session, None, None]:
    """Direct-DB session for setup/teardown in concurrency tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=concurrent_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def concurrent_client(concurrent_db_engine) -> Generator[TestClient, None, None]:
    """TestClient wired to the NullPool engine for concurrency testing."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=concurrent_db_engine)
    original_engine = database_module.engine
    original_session_local = database_module.SessionLocal

    database_module.engine = concurrent_db_engine
    database_module.SessionLocal = TestingSessionLocal

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    database_module.engine = original_engine
    database_module.SessionLocal = original_session_local

