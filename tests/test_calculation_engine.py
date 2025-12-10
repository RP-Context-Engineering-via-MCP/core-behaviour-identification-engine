import pytest
from src.services.calculation_engine import CalculationEngine


@pytest.fixture
def calc_engine():
    """Fixture for CalculationEngine"""
    return CalculationEngine()


def test_calculate_behavior_weight(calc_engine):
    """Test behavior weight calculation"""
    bw = calc_engine.calculate_behavior_weight(
        credibility=0.9,
        clarity_score=0.8,
        extraction_confidence=0.85
    )
    
    assert 0.0 <= bw <= 1.0
    assert isinstance(bw, float)


def test_calculate_adjusted_behavior_weight(calc_engine):
    """Test adjusted behavior weight calculation"""
    abw = calc_engine.calculate_adjusted_behavior_weight(
        behavior_weight=0.85,
        reinforcement_count=3,
        decay_rate=0.01,
        days_since_last_seen=5.0
    )
    
    assert abw > 0.0
    assert isinstance(abw, float)


def test_calculate_cluster_strength(calc_engine):
    """Test cluster strength calculation"""
    timestamps = [1730000000, 1730100000, 1730200000]
    
    strength = calc_engine.calculate_cluster_strength(
        cluster_size=5,
        mean_abw=0.85,
        timestamps=timestamps,
        current_timestamp=1730300000
    )
    
    assert 0.0 <= strength <= 1.0
    assert isinstance(strength, float)


def test_calculate_recency_factor(calc_engine):
    """Test recency factor calculation"""
    timestamps = [1730000000, 1730100000]
    current_time = 1730200000
    
    recency = calc_engine.calculate_recency_factor(
        timestamps=timestamps,
        current_timestamp=current_time
    )
    
    assert recency > 0.0
    assert isinstance(recency, float)
