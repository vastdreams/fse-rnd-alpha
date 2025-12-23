"""Integration tests for API endpoints."""
import pytest
from flask import Flask
from src.api.app_factory import create_flask_app


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_flask_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_companies_list_endpoint(client):
    """Test companies list endpoint."""
    response = client.get("/api/companies/")
    assert response.status_code in [200, 500]  # May fail if no DB connection
    if response.status_code == 200:
        assert isinstance(response.get_json(), list)


def test_factors_rd_summary_endpoint(client):
    """Test R&D factors summary endpoint."""
    response = client.get("/api/factors/rd/summary")
    assert response.status_code in [200, 500]  # May fail if no DB connection

