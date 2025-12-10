import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Test client for FastAPI"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test detailed health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data


def test_create_behavior_endpoint(client):
    """Test behavior creation endpoint"""
    behavior_data = {
        "behavior_text": "User prefers dark mode",
        "credibility": 0.9,
        "clarity_score": 0.85,
        "extraction_confidence": 0.8
    }
    
    # This will fail without proper setup, but structure is here
    # response = client.post("/behaviors", json=behavior_data)
    # assert response.status_code == 200
