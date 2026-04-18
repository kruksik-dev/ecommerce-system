import json
import os
import tempfile
from typing import Any, Generator

import pytest
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="function")
def db_engine() -> Generator[Engine, Any, None]:
    """Create test database engine and run migrations via Alembic"""
    # Create fresh temp DB for this test
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = db_url

    # Create engine with proper datetime handling for SQLite and Python 3.12+
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=StaticPool,
        echo=False,
        json_serializer=lambda obj: json.dumps(
            obj,
            default=str,  # Serialize datetime as ISO format string
        ),
    )

    # Fix SQLite datetime adapter warning for Python 3.12+
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        if "sqlite" in str(db_url).lower():
            # Use ISO format for datetime serialization
            dbapi_conn.isolation_level = None

    # Run Alembic migrations
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Warning: Alembic migration failed: {e}")
        print("This might be expected for in-memory databases")
        raise

    yield engine

    # Cleanup
    engine.dispose()
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session, Any, None]:
    """Create test database session"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()

    yield session

    session.close()
