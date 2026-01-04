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
        # Only include CORE epistemic state (supported latent preferences)
        canonical_behaviors = []
        
        for cluster in profile_data.get("behavior_clusters", []):
            # Filter by epistemic state (primary filter)
            epistemic_state = cluster.get("epistemic_state", "CORE")  # Default to CORE for backward compatibility
            
            if epistemic_state == "CORE":
                # Only expose CORE preferences (not INSUFFICIENT_EVIDENCE or NOISE)
                canonical_behaviors.append({
                    "cluster_id": cluster.get("cluster_id"),
                    "canonical_label": cluster.get("canonical_label"),
                    "cluster_name": cluster.get("cluster_name"),
                    "tier": cluster.get("tier"),
                    "cluster_strength": cluster.get("cluster_strength"),
                    "confidence": cluster.get("confidence"),  # Now uses stability-based confidence
                    "cluster_stability": cluster.get("cluster_stability"),  # Include stability score
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
        user_ids = mongodb_service.db.prompts.distinct("user_id")
        
        users = []
        for user_id in user_ids:
            prompt_count = mongodb_service.db.prompts.count_documents({"user_id": user_id})
            behavior_count = mongodb_service.db.behaviors.count_documents({"user_id": user_id})
            
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


@router.get(
    "/profile/{user_id}/analysis-summary",
    status_code=status.HTTP_200_OK,
    summary="Get complete analysis summary with 2D projections",
    description="Returns behaviors, clusters, and metrics with 2D UMAP projections for visualization"
)
async def get_analysis_summary(user_id: str):
    """
    Get comprehensive analysis data for dashboard visualization
    
    Returns:
    - behaviors: All observations with 2D coordinates
    - clusters: Cluster metadata with stability scores
    - metrics: Dashboard statistics
    
    This endpoint is optimized for frontend visualization needs.
    """
    try:
        from src.services.projection_service import project_embeddings_to_2d, normalize_2d_coordinates
        from src.models.schemas import EpistemicState
        
        logger.info(f"Fetching analysis summary for user {user_id}")
        
        # Get user profile
        profile_data = mongodb_service.get_profile(user_id)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for user {user_id}"
            )
        
        # Collect all embeddings and observations
        all_embeddings = []
        all_observations = []
        embedding_to_obs_map = []  # Track which embedding belongs to which observation
        
        for cluster in profile_data.get("behavior_clusters", []):
            cluster_id = cluster.get("cluster_id")
            cluster_name = cluster.get("cluster_name", cluster.get("canonical_label", "Unknown"))
            cluster_stability = cluster.get("cluster_stability", 0.0)
            epistemic_state = cluster.get("epistemic_state", "CORE")
            
            for obs in cluster.get("observations", []):
                embedding = obs.get("embedding")
                if embedding and len(embedding) > 0:
                    all_embeddings.append(embedding)
                    embedding_to_obs_map.append({
                        "observation": obs,
                        "cluster_id": cluster_id,
                        "cluster_name": cluster_name,
                        "cluster_stability": cluster_stability,
                        "epistemic_state": epistemic_state
                    })
        
        # Project embeddings to 2D
        if len(all_embeddings) == 0:
            logger.warning(f"No embeddings found for user {user_id}")
            projections_2d = []
        else:
            logger.info(f"Projecting {len(all_embeddings)} embeddings to 2D")
            projections_2d = project_embeddings_to_2d(all_embeddings)
            # Normalize to range [-10, 10] for consistent visualization
            projections_2d = normalize_2d_coordinates(projections_2d, target_range=(-10.0, 10.0))
        
        # Build behaviors array with 2D coordinates
        behaviors = []
        for i, (projection, mapping) in enumerate(zip(projections_2d, embedding_to_obs_map)):
            obs = mapping["observation"]
            behaviors.append({
                "id": obs.get("observation_id", f"obs_{i}"),
                "text": obs.get("behavior_text", ""),
                "credibility": obs.get("credibility", 0.0),
                "timestamp": obs.get("timestamp", 0),
                "source": "system",
                "embedding": projection,  # 2D coordinates {x, y}
                "clusterId": mapping["cluster_id"],
                "clusterName": mapping["cluster_name"],
                "clusterStability": mapping["cluster_stability"],
                "epistemicState": mapping["epistemic_state"]
            })
        
        # Build clusters array
        clusters = []
        for cluster in profile_data.get("behavior_clusters", []):
            epistemic_state = cluster.get("epistemic_state", "CORE")
            is_core = epistemic_state == "CORE"
            
            clusters.append({
                "id": cluster.get("cluster_id"),
                "name": cluster.get("cluster_name", cluster.get("canonical_label", "Unknown")),
                "stability": cluster.get("cluster_stability", 0.0),
                "size": cluster.get("cluster_size", 0),
                "isCore": is_core,
                "epistemicState": epistemic_state,
                "confidence": cluster.get("confidence", 0.0),
                "clusterStrength": cluster.get("cluster_strength", 0.0)
            })
        
        # Calculate metrics
        total_observations = sum(c["size"] for c in clusters)
        core_clusters = sum(1 for c in clusters if c["isCore"])
        insufficient_clusters = sum(1 for c in clusters if c.get("epistemicState") == "INSUFFICIENT_EVIDENCE")
        noise_clusters = sum(1 for c in clusters if c.get("epistemicState") == "NOISE")
        
        # Count observations by epistemic state
        insufficient_obs = sum(
            c["size"] for c in clusters 
            if c.get("epistemicState") == "INSUFFICIENT_EVIDENCE"
        )
        noise_obs = sum(
            c["size"] for c in clusters 
            if c.get("epistemicState") == "NOISE"
        )
        
        metrics = {
            "totalObservations": total_observations,
            "coreClusters": core_clusters,
            "insufficientEvidence": insufficient_obs,
            "noiseObservations": noise_obs,
            "totalClusters": len(clusters)
        }
        
        response = {
            "user_id": user_id,
            "behaviors": behaviors,
            "clusters": clusters,
            "metrics": metrics,
            "archetype": profile_data.get("archetype"),
            "generated_at": profile_data.get("generated_at", 0)
        }
        
        logger.info(
            f"Analysis summary complete: {len(behaviors)} behaviors, "
            f"{len(clusters)} clusters, {core_clusters} CORE"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analysis summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analysis summary: {str(e)}"
        )


@router.post(
    "/profile/{user_id}/simulate-threshold",
    status_code=status.HTTP_200_OK,
    summary="Simulate cluster classification with different stability threshold",
    description="Re-classify clusters based on new stability threshold without saving changes"
)
async def simulate_threshold(
    user_id: str,
    stability_threshold: float = 0.15
):
    """
    Interactive threshold tuning for the "Threshold Lab" feature
    
    Args:
        user_id: User identifier
        stability_threshold: New threshold to test (0.0 to 1.0)
        
    Returns:
        Updated cluster classifications and core count
    """
    try:
        logger.info(f"Simulating threshold {stability_threshold} for user {user_id}")
        
        # Get user profile
        profile_data = mongodb_service.get_profile(user_id)
        
        if not profile_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for user {user_id}"
            )
        
        # Re-classify clusters based on new threshold
        updated_clusters = []
        for cluster in profile_data.get("behavior_clusters", []):
            stability = cluster.get("cluster_stability", 0.0)
            
            # Determine new epistemic state based on threshold
            # Only clusters with stability >= threshold are considered CORE
            if stability >= stability_threshold:
                is_core = True
                new_state = "CORE"
            else:
                is_core = False
                # Keep original non-CORE state (INSUFFICIENT_EVIDENCE or NOISE)
                original_state = cluster.get("epistemic_state", "INSUFFICIENT_EVIDENCE")
                new_state = original_state if original_state != "CORE" else "INSUFFICIENT_EVIDENCE"
            
            updated_clusters.append({
                "id": cluster.get("cluster_id"),
                "name": cluster.get("cluster_name", cluster.get("canonical_label", "Unknown")),
                "stability": stability,
                "size": cluster.get("cluster_size", 0),
                "isCore": is_core,
                "epistemicState": new_state,
                "confidence": cluster.get("confidence", 0.0),
                "clusterStrength": cluster.get("cluster_strength", 0.0)
            })
        
        # Count new core clusters
        core_count = sum(1 for c in updated_clusters if c["isCore"])
        insufficient_count = sum(1 for c in updated_clusters if c["epistemicState"] == "INSUFFICIENT_EVIDENCE")
        noise_count = sum(1 for c in updated_clusters if c["epistemicState"] == "NOISE")
        
        # Calculate observation counts by state
        insufficient_obs = sum(c["size"] for c in updated_clusters if c["epistemicState"] == "INSUFFICIENT_EVIDENCE")
        noise_obs = sum(c["size"] for c in updated_clusters if c["epistemicState"] == "NOISE")
        
        response = {
            "user_id": user_id,
            "stability_threshold": stability_threshold,
            "coreClusters": core_count,
            "insufficientClusters": insufficient_count,
            "noiseClusters": noise_count,
            "metrics": {
                "coreClusters": core_count,
                "insufficientEvidence": insufficient_obs,
                "noiseObservations": noise_obs
            },
            "updated_clusters": updated_clusters
        }
        
        logger.info(
            f"Threshold simulation complete: {core_count} CORE clusters "
            f"(threshold={stability_threshold})"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating threshold: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to simulate threshold: {str(e)}"
        )

