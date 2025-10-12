from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BehaviorModel(BaseModel):
    """Model representing a user behavior observation"""
    
    behavior_id: str = Field(..., description="Unique identifier for the behavior")
    behavior_text: str = Field(..., description="The behavior observation text")
    credibility: float = Field(default=1.0, ge=0.0, le=1.0, description="Credibility score")
    clarity_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Clarity of the behavior")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in extraction")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the behavior was observed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "behavior_id": "behav_001",
                "behavior_text": "User prefers dark mode interfaces",
                "credibility": 0.95,
                "clarity_score": 0.9,
                "extraction_confidence": 0.85,
                "timestamp": "2025-10-12T16:30:00Z"
            }
        }
