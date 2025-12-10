"""
FastAPI routes for CBIE System
Implements 5 API endpoints as specified in MVP documentation
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
import logging

from src.models.schemas import (
    AnalyzeBehaviorsRequest,
    AnalyzeBehaviorsResponse,
    CoreBehaviorProfile,
    UpdateBehaviorRequest,
    AssignArchetypeRequest,
    AssignArchetypeResponse,
    ListCoreBehaviorsResponse,
    BehaviorObservation
)
from src.services.analysis_pipeline import analysis_pipeline
from src.services.cluster_analysis_pipeline import cluster_analysis_pipeline
from src.services.llm_context_service import generate_llm_context
from src.database.mongodb_service import mongodb_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze-behaviors-from-storage",
    response_model=AnalyzeBehaviorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze behaviors from existing storage (NORMAL SCENARIO)",
    description="Fetch behaviors from Qdrant (with embeddings) and prompts from MongoDB, "
                "then run analysis pipeline. This is the typical production workflow."
)
async def analyze_behaviors_from_storage(user_id: str):
    """
    Analyze user behaviors from existing storage (PRODUCTION SCENARIO)
    
    In normal operation:
    - Behaviors are stored in Qdrant vector database (with embeddings)
    - Prompts are stored in MongoDB
    
    This endpoint:
    1. Fetches behaviors from Qdrant (already embedded)
    2. Fetches prompts from MongoDB
    3. Calculates behavior weights (BW, ABW)
    4. Performs clustering using existing embeddings
    5. Assigns tiers (PRIMARY/SECONDARY/NOISE)
    6. Calculates temporal metrics
    7. Generates archetype (optional)
    8. Stores and returns profile
    """
    try:
        logger.info(f"Received analysis request from storage for user {user_id}")
        
        # Run cluster-centric analysis pipeline from storage
        profile = await cluster_analysis_pipeline.analyze_behaviors_from_storage(
            user_id=user_id,
            generate_archetype=True
        )
        
        return profile
        
    except ValueError as e:
        logger.error(f"User data not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in analyze_behaviors_from_storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post(
    "/analyze-behaviors",
    response_model=AnalyzeBehaviorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze new behaviors and store in databases",
    description="Import new behaviors and prompts, generate embeddings, store everything, "
                "then run analysis. Use this for test data or bulk imports."
)
async def analyze_behaviors(request: AnalyzeBehaviorsRequest):
    """
    Analyze user behaviors with new data (TEST/IMPORT SCENARIO)
    
    This endpoint is used for:
    - Testing with sample data
    - Bulk importing new behaviors
    - Initial data setup
    
    It will:
    1. Store prompts in MongoDB
    2. Generate embeddings for behaviors
    3. Store behaviors with embeddings in Qdrant
    4. Store behavior metadata in MongoDB
    5. Calculate behavior weights (BW, ABW)
    6. Perform clustering (HDBSCAN)
    7. Assign tiers (PRIMARY/SECONDARY/NOISE)
    8. Calculate temporal metrics
    9. Generate archetype (optional)
    10. Store and return profile
    """
    try:
        logger.info(
            f"Received analyze request with new data for user {request.user_id}: "
            f"{len(request.behaviors)} behaviors, {len(request.prompts)} prompts"
        )
        
        # Run analysis pipeline with storage
        profile = await analysis_pipeline.analyze_behaviors(
            user_id=request.user_id,
            behaviors=request.behaviors,
            prompts=request.prompts,
            generate_archetype=True,
            store_in_dbs=True
        )
        
        return profile
        
    except Exception as e:
        logger.error(f"Error in analyze_behaviors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "/get-user-profile/{user_id}",
    response_model=CoreBehaviorProfile,
    status_code=status.HTTP_200_OK,
    summary="Retrieve user's core behavior profile",
    description="Get existing core behavior profile for a specific user. Embeddings are excluded from response."
)
async def get_user_profile(user_id: str):
    """
    Retrieve a user's existing core behavior profile from database
    Embeddings are stripped from clusters and observations for performance
    """
    try:
        logger.info(f"Fetching profile for user {user_id}")
        
        profile_data = mongodb_service.get_profile(user_id)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for user {user_id}"
            )
        
        # Strip embeddings from clusters to reduce payload size
        if "behavior_clusters" in profile_data:
            for cluster in profile_data["behavior_clusters"]:
                # Remove centroid embedding
                cluster.pop("centroid_embedding", None)
                
                # Remove embeddings from observations
                if "observations" in cluster:
                    for obs in cluster["observations"]:
                        obs.pop("embedding", None)
        
        # Convert to Pydantic model
        profile = CoreBehaviorProfile(**profile_data)
        
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(e)}"
        )


@router.get(
    "/list-core-behaviors/{user_id}",
    response_model=ListCoreBehaviorsResponse,
    status_code=status.HTTP_200_OK,
    summary="List canonical core behaviors for a user",
    description="Return canonical behaviors from behavior clusters for downstream context usage. No embeddings included."
)
async def list_core_behaviors(user_id: str):
    """
    Get list of canonical core behaviors (PRIMARY and SECONDARY) from stored profile
    
    Returns cluster-based canonical behaviors without embeddings:
    - canonical_label: Display text for the cluster
    - tier: PRIMARY/SECONDARY (NOISE clusters excluded)
    - cluster_strength: Strength score
    - confidence: Confidence score
    - observed_count: Number of observations in cluster
    """
    try:
        logger.info(f"Listing core behaviors for user {user_id}")
        
        profile_data = mongodb_service.get_profile(user_id)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for user {user_id}"
            )
        
        # Extract canonical behaviors from behavior_clusters
        canonical_behaviors = []
        
        for cluster in profile_data.get("behavior_clusters", []):
            # Only include PRIMARY and SECONDARY (exclude NOISE)
            if cluster.get("tier") in ["PRIMARY", "SECONDARY"]:
                canonical_behaviors.append({
                    "cluster_id": cluster.get("cluster_id"),
                    "canonical_label": cluster.get("canonical_label"),
                    "cluster_name": cluster.get("cluster_name"),
                    "tier": cluster.get("tier"),
                    "cluster_strength": cluster.get("cluster_strength"),
                    "confidence": cluster.get("confidence"),  # Maps confidence from DB
                    "observed_count": cluster.get("cluster_size")  # Maps cluster_size from DB
                    # Note: embeddings are NOT included
                })
        
        return ListCoreBehaviorsResponse(
            user_id=user_id,
            canonical_behaviors=canonical_behaviors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing behaviors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list behaviors: {str(e)}"
        )


@router.post(
    "/update-behavior",
    response_model=BehaviorObservation,
    status_code=status.HTTP_200_OK,
    summary="Update behavior metadata",
    description="Update reinforcement, credibility, or timestamps of a behavior"
)
async def update_behavior(request: UpdateBehaviorRequest):
    """
    Update behavior document with new values
    
    Allowed updates:
    - reinforcement_count
    - credibility
    - clarity_score
    - extraction_confidence
    - last_seen
    - decay_rate
    """
    try:
        logger.info(f"Updating behavior {request.behavior_id}: {request.updates}")
        
        # Validate behavior exists
        behavior_data = mongodb_service.get_behavior(request.behavior_id)
        if not behavior_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Behavior {request.behavior_id} not found"
            )
        
        # Update behavior
        success = await analysis_pipeline.update_behavior_metrics(
            request.behavior_id,
            request.updates
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update behavior"
            )
        
        # Fetch updated behavior
        updated_data = mongodb_service.get_behavior(request.behavior_id)
        updated_behavior = BehaviorObservation(**updated_data)
        
        return updated_behavior
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating behavior: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )


@router.post(
    "/assign-archetype",
    response_model=AssignArchetypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign behavioral archetype label",
    description="Use LLM to generate and assign archetype label to user profile"
)
async def assign_archetype(request: AssignArchetypeRequest):
    """
    Generate behavioral archetype label using LLM
    
    Can provide canonical behaviors explicitly, or will fetch from existing profile
    """
    try:
        logger.info(
            f"Assigning archetype for user {request.user_id} "
            f"with {len(request.canonical_behaviors)} behaviors"
        )
        
        # Generate and assign archetype
        archetype = await analysis_pipeline.assign_archetype_to_profile(
            user_id=request.user_id,
            canonical_behaviors=request.canonical_behaviors if request.canonical_behaviors else None
        )
        
        if not archetype:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate archetype"
            )
        
        return AssignArchetypeResponse(
            user_id=request.user_id,
            archetype=archetype
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning archetype: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Archetype assignment failed: {str(e)}"
        )


@router.post(
    "/analyze-behaviors-cluster-centric",
    response_model=CoreBehaviorProfile,
    status_code=status.HTTP_200_OK,
    summary="[NEW] Analyze behaviors using cluster-centric pipeline",
    description="Test the NEW cluster-centric implementation where clusters are primary entities. "
                "Returns behavior_clusters[] with full aggregated evidence."
)
async def analyze_behaviors_cluster_centric(request: AnalyzeBehaviorsRequest):
    """
    NEW CLUSTER-CENTRIC analysis pipeline
    
    Key differences from old pipeline:
    - Clusters are PRIMARY entities (not individual behaviors)
    - ALL observations in clusters are preserved
    - Scoring based on cluster_strength (log-scaled with recency)
    - Confidence from cluster consistency, not single observation
    - Returns behavior_clusters[] with full evidence aggregation
    
    Response includes:
    - behavior_clusters[] - list of BehaviorCluster objects
    - Each cluster contains:
      * canonical_label (UI only)
      * cluster_strength (log(size) * mean_abw * recency)
      * confidence (consistency * reinforcement * clarity_trend)
      * observed_count (cluster_size)
      * wording_variations[] (all phrasings)
      * all_prompt_ids[] (evidence)
      * all_timestamps[] (temporal data)
      * first_seen, last_seen, days_active
      * tier (PRIMARY/SECONDARY/NOISE)
    """
    try:
        from src.services.cluster_analysis_pipeline import cluster_analysis_pipeline
        from src.models.schemas import BehaviorObservation, PromptModel
        import time
        
        logger.info(
            f"[CLUSTER-CENTRIC] Analyzing {len(request.behaviors)} observations "
            f"and {len(request.prompts)} prompts for user {request.user_id}"
        )
        
        # Convert incoming data to BehaviorObservation if needed
        observations = []
        for b in request.behaviors:
            # Check if it's already a BehaviorObservation or needs conversion
            if isinstance(b, BehaviorObservation):
                observations.append(b)
            else:
                # Convert from dict or old format
                obs = BehaviorObservation(
                    observation_id=getattr(b, 'observation_id', getattr(b, 'behavior_id', 'unknown')),
                    behavior_text=b.behavior_text,
                    credibility=b.credibility,
                    clarity_score=b.clarity_score,
                    extraction_confidence=b.extraction_confidence,
                    timestamp=getattr(b, 'timestamp', getattr(b, 'created_at', 0)),
                    prompt_id=getattr(b, 'prompt_id', b.prompt_history_ids[0] if hasattr(b, 'prompt_history_ids') and b.prompt_history_ids else 'unknown'),
                    decay_rate=b.decay_rate,
                    user_id=b.user_id,
                    session_id=b.session_id
                )
                observations.append(obs)
        
        # Run cluster-centric analysis
        profile = await cluster_analysis_pipeline.analyze_observations(
            user_id=request.user_id,
            observations=observations,
            prompts=request.prompts,
            generate_archetype=True,
            store_in_dbs=False  # Don't store yet - this is for testing
        )
        
        logger.info(
            f"[CLUSTER-CENTRIC] Analysis complete: {len(profile.behavior_clusters)} clusters formed"
        )
        
        return profile
        
    except Exception as e:
        logger.error(f"Error in cluster-centric analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cluster-centric analysis failed: {str(e)}"
        )


# Health check endpoint
@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if API is running"
)
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "CBIE MVP"}


@router.get(
    "/profile/{user_id}/llm-context",
    status_code=status.HTTP_200_OK,
    summary="Get LLM context for user",
    description="Generate formatted behavioral context for LLM prompt injection. "
                "Returns top behaviors ranked by strength with wording variations."
)
async def get_llm_context(
    user_id: str,
    min_strength: float = 30.0,
    min_confidence: float = 0.40,
    max_behaviors: int = 5,
    include_archetype: bool = True
):
    """
    Generate LLM-ready behavioral context for personalized responses.
    
    Args:
        user_id: User identifier
        min_strength: Minimum cluster strength percentage (0-100)
        min_confidence: Minimum confidence score (0-1.0)
        max_behaviors: Maximum number of behaviors to include
        include_archetype: Whether to include archetype description
    
    Returns:
        Dict with formatted context string and metadata
    """
    try:
        logger.info(f"Generating LLM context for user {user_id}")
        
        context_data = await generate_llm_context(
            user_id=user_id,
            min_strength=min_strength,
            min_confidence=min_confidence,
            max_behaviors=max_behaviors,
            include_archetype=include_archetype
        )
        
        if not context_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for user {user_id}"
            )
        
        return context_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating LLM context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate LLM context: {str(e)}"
        )


@router.get(
    "/test-users",
    status_code=status.HTTP_200_OK,
    summary="List available test users in database",
    description="Get list of users with prompts and behaviors in the database for demo/testing"
)
async def get_test_users():
    """
    List all users that have data in MongoDB
    Returns user_id, prompt count, and behavior count for each user
    """
    try:
        # Get all unique user IDs from prompts collection
        user_ids = mongodb_service.prompts.distinct("user_id")
        
        users = []
        for user_id in user_ids:
            prompt_count = mongodb_service.prompts.count_documents({"user_id": user_id})
            behavior_count = mongodb_service.behaviors.count_documents({"user_id": user_id})
            
            users.append({
                "user_id": user_id,
                "prompt_count": prompt_count,
                "behavior_count": behavior_count
            })
        
        return {"users": users, "total": len(users)}
        
    except Exception as e:
        logger.error(f"Error fetching test users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test users: {str(e)}"
        )
