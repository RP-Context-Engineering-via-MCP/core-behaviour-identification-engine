import pytest


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connection"""
    pass


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "test_user_001"


@pytest.fixture
def sample_behavior_data():
    """Sample behavior observation data"""
    return {
        "observation_id": "obs_001",
        "behavior_text": "prefers visual learning",
        "credibility": 0.9,
        "clarity_score": 0.8,
        "extraction_confidence": 0.85,
        "timestamp": 1730000000
    }
