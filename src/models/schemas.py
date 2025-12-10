"""
Pydantic schemas for CBIE data models
Based on CBIE MVP Documentation specifications
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TierEnum(str, Enum):
    """Behavior tier classification"""
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    NOISE = "NOISE"


class BehaviorObservation(BaseModel):
    """
    Single observation of a behavior (was BehaviorModel)
    This is NOT the primary entity anymore - clusters are.
    """
    observation_id: str  # formerly behavior_id
    behavior_text: str
    embedding: Optional[List[float]] = None  # Store embedding with observation
    
    # Individual observation metrics
    credibility: float = Field(ge=0.0, le=1.0)
    clarity_score: float = Field(ge=0.0, le=1.0)
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    
    # Temporal data
    timestamp: int  # Unix timestamp - when observed
    prompt_id: str  # Which prompt triggered this observation
    
    # Legacy fields for backward compatibility
    decay_rate: float = Field(ge=0.0, default=0.01)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Calculated metrics (populated during analysis)
    bw: Optional[float] = None  # Behavior Weight
    abw: Optional[float] = None  # Adjusted Behavior Weight
    
    class Config:
        json_schema_extra = {
            "example": {
                "observation_id": "obs_3ccbf2b2",
                "behavior_text": "prefers visual learning",
                "credibility": 0.95,
                "clarity_score": 0.76,
                "extraction_confidence": 0.77,
                "timestamp": 1765741962,
                "prompt_id": "prompt_1",
                "decay_rate": 0.012,
                "user_id": "user_348",
                "session_id": "session_7732"
            }
        }


# Keep BehaviorModel as alias for backward compatibility during migration
BehaviorModel = BehaviorObservation


class PromptModel(BaseModel):
    """User prompt object"""
    prompt_id: str
    prompt_text: str
    timestamp: int  # Unix timestamp
    tokens: Optional[float] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt_id": "prompt_1",
                "prompt_text": "Visualize the HTTP request lifecycle",
                "timestamp": 1761637013,
                "tokens": 12.0,
                "user_id": "user_348",
                "session_id": "session_7732"
            }
        }


class TemporalSpan(BaseModel):
    """Temporal metrics for a behavior"""
    first_seen: int
    last_seen: int
    days_active: float


class BehaviorCluster(BaseModel):
    """
    PRIMARY ENTITY: A cluster of semantically similar behavior observations
    This is what matters - not individual behaviors.
    """
    cluster_id: str
    user_id: str
    
    # ALL observations in this cluster (NEVER discard any)
    observation_ids: List[str]
    observations: List[BehaviorObservation] = []  # Full observation data
    
    # Cluster metadata
    centroid_embedding: Optional[List[float]] = None
    cluster_size: int  # len(observations)
    
    # Display label (UI only - NOT used for scoring)
    canonical_label: str  # LLM-generated or longest/most descriptive text
    canonical_observation_id: Optional[str] = None  # Deprecated: kept for backward compatibility
    cluster_name: Optional[str] = None  # LLM-generated descriptive name for the cluster
    
    # Cluster-level metrics (the REAL scores)
    cluster_strength: float  # Normalized: log(size+1) * mean(ABW) * recency_factor / (1 + raw)
    confidence: float  # Multiplicative: consistency * reinforcement
    
    # Aggregated evidence
    all_prompt_ids: List[str]  # All prompts that triggered observations
    all_timestamps: List[int]  # All observation timestamps
    wording_variations: List[str]  # Different phrasings of same concept
    
    # Temporal tracking
    first_seen: int  # Earliest observation timestamp
    last_seen: int   # Latest observation timestamp
    days_active: float  # (last_seen - first_seen) / 86400
    
    # Tier classification (based on cluster_strength, not canonical)
    tier: TierEnum
    
    # Cluster evolution tracking
    created_at: int  # When cluster was first formed
    updated_at: int  # Last update to cluster
    
    # Internal metrics for confidence calculation
    consistency_score: Optional[float] = None  # How similar members are
    reinforcement_score: Optional[float] = None  # How often it reappears
    clarity_trend: Optional[float] = None  # Improving or degrading
    mean_abw: Optional[float] = None  # Mean ABW of observations
    recency_factor: Optional[float] = None  # Weighted decay
    
    class Config:
        json_schema_extra = {
            "example": {
                "cluster_id": "cluster_0",
                "user_id": "user_348",
                "observation_ids": ["obs_1", "obs_2", "obs_3"],
                "cluster_size": 3,
                "canonical_label": "prefers visual learning",
                "canonical_observation_id": "obs_1",
                "cluster_strength": 2.87,
                "confidence": 0.85,
                "all_prompt_ids": ["prompt_1", "prompt_5", "prompt_12"],
                "all_timestamps": [1765741962, 1765828362, 1766000000],
                "wording_variations": [
                    "prefers visual learning",
                    "likes visual explanations", 
                    "learns best through diagrams"
                ],
                "first_seen": 1765741962,
                "last_seen": 1766000000,
                "days_active": 2.99,
                "tier": "PRIMARY",
                "created_at": 1765741962,
                "updated_at": 1766000000
            }
        }


class CanonicalBehavior(BaseModel):
    """DEPRECATED: Legacy model for backward compatibility"""
    behavior_id: str
    behavior_text: str
    cluster_id: str
    cbi_original: float  # Individual ABW
    cluster_cbi: float   # Cluster average
    tier: TierEnum
    temporal_span: TemporalSpan


class ProfileStatistics(BaseModel):
    """Statistics for core behavior profile"""
    total_behaviors_analyzed: int
    clusters_formed: int
    total_prompts_analyzed: int
    analysis_time_span_days: float


class CoreBehaviorProfile(BaseModel):
    """
    Complete user core behavior profile
    NOW CLUSTER-CENTRIC: clusters are the primary data structure
    """
    user_id: str
    generated_at: int  # Unix timestamp
    
    # NEW: Clusters are primary (not individual behaviors)
    behavior_clusters: List[BehaviorCluster] = []
    
    # DEPRECATED: Keep for backward compatibility
    primary_behaviors: List[CanonicalBehavior] = []
    secondary_behaviors: List[CanonicalBehavior] = []
    
    archetype: Optional[str] = None
    statistics: ProfileStatistics
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_348",
                "generated_at": 1766000000,
                "behavior_clusters": [],
                "primary_behaviors": [],
                "secondary_behaviors": [],
                "archetype": "Visual Learner",
                "statistics": {
                    "total_behaviors_analyzed": 5,
                    "clusters_formed": 3,
                    "total_prompts_analyzed": 50,
                    "analysis_time_span_days": 60
                }
            }
        }


class ClusterModel(BaseModel):
    """DEPRECATED: Use BehaviorCluster instead"""
    cluster_id: str
    user_id: str
    behavior_ids: List[str]
    canonical_behavior_id: str
    cluster_cbi: float
    tier: TierEnum
    created_at: int


# API Request/Response Models

class AnalyzeBehaviorsRequest(BaseModel):
    """Request body for /analyze-behaviors endpoint"""
    user_id: str
    behaviors: List[BehaviorModel]
    prompts: List[PromptModel]


class AnalyzeBehaviorsResponse(CoreBehaviorProfile):
    """Response for /analyze-behaviors endpoint"""
    pass


class UpdateBehaviorRequest(BaseModel):
    """Request body for /update-behavior endpoint"""
    behavior_id: str
    updates: Dict[str, Any]


class AssignArchetypeRequest(BaseModel):
    """Request body for /assign-archetype endpoint"""
    user_id: str
    canonical_behaviors: List[str]  # List of behavior texts


class AssignArchetypeResponse(BaseModel):
    """Response for /assign-archetype endpoint"""
    user_id: str
    archetype: str


class ListCoreBehaviorsResponse(BaseModel):
    """Response for /list-core-behaviors endpoint"""
    user_id: str
    canonical_behaviors: List[Dict[str, Any]]  # Changed from str to Any to support multiple types
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_102",
                "canonical_behaviors": [
                    {
                        "cluster_id": "cluster_2",
                        "canonical_label": "prefers analogies and metaphors",
                        "cluster_name": "Visual Learning Preference",
                        "tier": "PRIMARY",
                        "cluster_strength": 0.8421,
                        "confidence": 0.6232,
                        "observed_count": 4
                    },
                    {
                        "cluster_id": "cluster_0",
                        "canonical_label": "theory and concept focused",
                        "cluster_name": "Conceptual Understanding Focus",
                        "tier": "SECONDARY",
                        "cluster_strength": 0.7783,
                        "confidence": 0.5120,
                        "observed_count": 2
                    }
                ]
            }
        }
