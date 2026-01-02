from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TierEnum(str, Enum):
    """Behavior tier classification"""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    NOISE = "NOISE"


class BehaviorObservation(BaseModel):
    """
    Single observation of a behavior (renamed from BehaviorModel)
    Represents an individual behavior observation
    """
    observation_id: str = Field(..., description="Unique identifier (formerly behavior_id)")
    behavior_text: str = Field(..., description="The behavior observation text")
    embedding: Optional[List[float]] = None
    
    # Individual observation metrics
    credibility: float = Field(default=1.0, ge=0.0, le=1.0, description="Credibility score")
    clarity_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Clarity of the behavior")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in extraction")
    
    # Temporal data
    timestamp: int = Field(..., description="Unix timestamp when observed")
    prompt_id: Optional[str] = None
    
    # Calculated metrics
    bw: Optional[float] = None  # Behavior Weight
    abw: Optional[float] = None  # Adjusted Behavior Weight
    
    class Config:
        json_schema_extra = {
            "example": {
                "observation_id": "obs_001",
                "behavior_text": "User prefers dark mode interfaces",
                "credibility": 0.95,
                "clarity_score": 0.9,
                "extraction_confidence": 0.85,
                "timestamp": 1730000000
            }
        }


# Alias for backward compatibility
BehaviorModel = BehaviorObservation


class BehaviorCluster(BaseModel):
    """
    A cluster of semantically similar behavior observations
    Primary entity in the cluster-centric architecture
    """
    cluster_id: str
    user_id: str
    
    # All observations in this cluster
    observation_ids: List[str]
    observations: List[BehaviorObservation] = []
    
    # Cluster metadata
    centroid_embedding: Optional[List[float]] = None
    cluster_size: int
    
    # Display label
    canonical_label: str
    canonical_observation_id: Optional[str] = None
    
    # Cluster-level metrics
    cluster_strength: float
    confidence: float
    
    # Aggregated evidence
    all_prompt_ids: List[str] = []
    all_timestamps: List[int] = []
    
    # Temporal tracking
    first_seen: int
    last_seen: int
    days_active: float
    
    # Tier classification
    tier: TierEnum
    
    # Timestamps
    created_at: int
    updated_at: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "cluster_id": "cluster_0",
                "user_id": "user_348",
                "observation_ids": ["obs_1", "obs_2"],
                "cluster_size": 2,
                "canonical_label": "prefers visual learning",
                "cluster_strength": 0.85,
                "confidence": 0.78,
                "first_seen": 1730000000,
                "last_seen": 1730100000,
                "days_active": 1.16,
                "tier": "PRIMARY",
                "created_at": 1730000000,
                "updated_at": 1730100000
            }
        }
