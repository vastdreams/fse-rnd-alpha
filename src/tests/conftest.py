"""Pytest configuration and fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.base import Base
from src.db.connection import get_engine, init_engine
from config.settings import get_settings


@pytest.fixture(scope="session")
def test_db_url():
    """Get test database URL."""
    settings = get_settings()
    # Use test database if specified, otherwise use in-memory SQLite
    return getattr(settings, "TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="function")
def db_session(test_db_url):
    """Create a test database session."""
    engine = create_engine(test_db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    return get_settings()

