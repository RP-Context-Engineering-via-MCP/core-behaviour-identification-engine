from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import logging

from src.services.embedding_service import EmbeddingService
from src.services.calculation_engine import CalculationEngine

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
embedding_service = EmbeddingService()
calc_engine = CalculationEngine()


class BehaviorInput(BaseModel):
    """Input model for behavior submission"""
    behavior_text: str
    credibility: float = 1.0
    clarity_score: float = 1.0
    extraction_confidence: float = 1.0


class BehaviorResponse(BaseModel):
    """Response model for behavior submission"""
    behavior_id: str
    behavior_text: str
    behavior_weight: float
    embedding_length: int
    timestamp: datetime


@router.post("/behaviors", response_model=BehaviorResponse)
async def create_behavior(behavior: BehaviorInput):
    """
    Ingest a new behavior observation
    
    - Generates embedding
    - Calculates behavior weight
    - Saves to MongoDB
    """
    try:
        # Generate unique ID
        behavior_id = f"behav_{uuid.uuid4().hex[:12]}"
        
        # Generate embedding
        embedding = embedding_service.get_embedding(behavior.behavior_text)
        
        # Calculate weight
        behavior_weight = calc_engine.calculate_behavior_weight(
            credibility=behavior.credibility,
            clarity_score=behavior.clarity_score,
            extraction_confidence=behavior.extraction_confidence
        )
        
        # TODO: Save to MongoDB
        logger.info(f"Created behavior {behavior_id} with weight {behavior_weight:.6f}")
        
        return BehaviorResponse(
            behavior_id=behavior_id,
            behavior_text=behavior.behavior_text,
            behavior_weight=behavior_weight,
            embedding_length=len(embedding),
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Failed to create behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/behaviors/{behavior_id}")
async def get_behavior(behavior_id: str):
    """Retrieve a behavior by ID"""
    # TODO: Implement MongoDB lookup
    return {"message": "Not yet implemented", "behavior_id": behavior_id}
