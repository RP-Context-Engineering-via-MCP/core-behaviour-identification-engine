"""
⚠️⚠️⚠️ DEPRECATED - DO NOT USE ⚠️⚠️⚠️

THIS FILE IS NO LONGER USED IN THE SYSTEM!

Analysis Pipeline for CBIE System (OLD OBSERVATION-CENTRIC APPROACH)

REPLACED BY: cluster_analysis_pipeline.py (NEW CLUSTER-CENTRIC APPROACH)

This file implements the OLD pipeline where individual behaviors were primary entities.
The system now uses a cluster-centric approach where clusters are the primary entities.

STATUS: Kept for reference only. Not called by any active code.
LAST USED: Before December 2025
REPLACEMENT: src/services/cluster_analysis_pipeline.py

⚠️⚠️⚠️ DEPRECATED - DO NOT USE ⚠️⚠️⚠️
"""
from typing import List, Dict, Any, Optional
import time
import logging

from src.models.schemas import (
    BehaviorObservation,
    PromptModel,
    CoreBehaviorProfile,
    CanonicalBehavior,
    TemporalSpan,
    ProfileStatistics,
    ClusterModel,
    TierEnum
)
from src.services.calculation_engine import calculation_engine
from src.services.embedding_service import embedding_service
from src.services.clustering_engine import clustering_engine
from src.services.archetype_service import archetype_service
from src.database.mongodb_service import mongodb_service
from src.database.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Main pipeline for analyzing behaviors and generating core behavior profiles"""
    
    def __init__(self):
        self.calculation_engine = calculation_engine
        self.embedding_service = embedding_service
        self.clustering_engine = clustering_engine
        self.archetype_service = archetype_service
        self.mongodb = mongodb_service
        self.qdrant = qdrant_service
    
    async def analyze_behaviors_from_storage(
        self,
        user_id: str,
        generate_archetype: bool = True,
        current_timestamp: Optional[int] = None
    ) -> CoreBehaviorProfile:
        """
        Analyze behaviors from existing storage (NORMAL SCENARIO)
        
        In production, behaviors are already stored in Qdrant (with embeddings)
        and prompts are stored in MongoDB. This method fetches from storage.
        
        Pipeline steps:
        1. Fetch behaviors from Qdrant (with embeddings)
        2. Fetch prompts from MongoDB
        3. Calculate BW and ABW for all behaviors
        4. Perform HDBSCAN clustering using existing embeddings
        5. Calculate Cluster CBI for each cluster
        6. Select canonical behavior per cluster
        7. Assign tiers (PRIMARY/SECONDARY/NOISE)
        8. Calculate temporal metrics
        9. Optional: Generate archetype via LLM
        10. Store profile in MongoDB
        11. Return CoreBehaviorProfile
        
        Args:
            user_id: User identifier
            generate_archetype: Whether to generate archetype label
            current_timestamp: Optional current timestamp (defaults to now)
            
        Returns:
            CoreBehaviorProfile: Complete profile with primary/secondary behaviors
        """
        try:
            if current_timestamp is None:
                current_timestamp = int(time.time())
            
            logger.info(f"Starting analysis from storage for user {user_id}")
            
            # Step 1: Fetch behaviors from Qdrant (already embedded)
            logger.info("Step 1: Fetching behaviors from Qdrant")
            qdrant_behaviors = self.qdrant.get_embeddings_by_user(user_id)
            
            if not qdrant_behaviors:
                raise ValueError(f"No behaviors found in Qdrant for user {user_id}")
            
            # Extract embeddings and behavior metadata
            embeddings = [qb["vector"] for qb in qdrant_behaviors]
            behavior_ids = [qb["payload"].get("behavior_id", qb["payload"].get("observation_id")) for qb in qdrant_behaviors]
            
            # Step 2: Construct behaviors from Qdrant (source of truth for embeddings)
            logger.info("Step 2: Constructing behavior objects from Qdrant payload")
            behavior_models = self._construct_behaviors_from_qdrant(qdrant_behaviors)
            
            logger.info(f"Loaded {len(behavior_models)} behaviors from Qdrant")
            
            # Step 3: Fetch prompts from MongoDB
            logger.info("Step 3: Fetching prompts from MongoDB")
            prompts_data = self.mongodb.get_prompts_by_user(user_id)
            prompts = [PromptModel(**p) for p in prompts_data]
            
            logger.info(f"Loaded {len(behavior_models)} behaviors and {len(prompts)} prompts")
            
            # Step 4: Calculate metrics for all behaviors
            logger.info("Step 4: Calculating behavior metrics (BW, ABW)")
            behavior_metrics = self.calculation_engine.calculate_all_metrics_batch(
                behavior_models, 
                current_timestamp
            )
            
            # Step 5: Perform clustering using existing embeddings
            logger.info("Step 5: Performing HDBSCAN clustering on stored embeddings")
            clustering_result = self.clustering_engine.cluster_behaviors(
                embeddings=embeddings,
                behavior_ids=behavior_ids
            )
            
            # Step 6-8: Process clusters
            logger.info("Step 6-8: Processing clusters (CBI, canonical, tiers)")
            primary_behaviors, secondary_behaviors, clusters_formed = \
                self._process_clusters(
                    clustering_result,
                    behavior_models,
                    behavior_metrics,
                    prompts
                )
            
            # Step 9: Calculate overall statistics
            logger.info("Step 9: Calculating profile statistics")
            time_span_days = self._calculate_time_span(prompts)
            
            statistics = ProfileStatistics(
                total_behaviors_analyzed=len(behavior_models),
                clusters_formed=clusters_formed,
                total_prompts_analyzed=len(prompts),
                analysis_time_span_days=time_span_days
            )
            
            # Step 10: Generate archetype (optional)
            archetype = None
            if generate_archetype and (primary_behaviors or secondary_behaviors):
                logger.info("Step 10: Generating behavioral archetype")
                canonical_texts = [
                    b.behavior_text 
                    for b in primary_behaviors + secondary_behaviors
                ]
                archetype = self.archetype_service.generate_archetype(
                    canonical_texts,
                    user_id
                )
            
            # Step 11: Create profile
            profile = CoreBehaviorProfile(
                user_id=user_id,
                generated_at=current_timestamp,
                primary_behaviors=primary_behaviors,
                secondary_behaviors=secondary_behaviors,
                archetype=archetype,
                statistics=statistics
            )
            
            # Step 12: Store in MongoDB
            logger.info("Step 12: Storing profile in MongoDB")
            self.mongodb.insert_profile(profile)
            
            logger.info(
                f"Analysis complete for user {user_id}: "
                f"{len(primary_behaviors)} PRIMARY, {len(secondary_behaviors)} SECONDARY"
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error in analysis pipeline from storage: {e}")
            raise
    
    async def analyze_behaviors(
        self,
        user_id: str,
        behaviors: List[BehaviorObservation],
        prompts: List[PromptModel],
        generate_archetype: bool = True,
        current_timestamp: Optional[int] = None,
        store_in_dbs: bool = True
    ) -> CoreBehaviorProfile:
        """
        Complete analysis pipeline with new data (TEST/IMPORT SCENARIO)
        
        This is used when importing new behaviors (e.g., from test data or bulk import).
        It generates embeddings, stores in Qdrant, and stores prompts in MongoDB.
        
        Pipeline steps:
        1. Store prompts in MongoDB
        2. Calculate BW and ABW for all behaviors
        3. Generate embeddings for behavior texts
        4. Store behaviors with embeddings in Qdrant
        5. Optionally store behavior metadata in MongoDB
        6. Perform HDBSCAN clustering
        7. Calculate Cluster CBI for each cluster
        8. Select canonical behavior per cluster
        9. Assign tiers (PRIMARY/SECONDARY/NOISE)
        10. Calculate temporal metrics
        11. Optional: Generate archetype via LLM
        12. Store profile in MongoDB
        13. Return CoreBehaviorProfile
        
        Args:
            user_id: User identifier
            behaviors: List of BehaviorObservation instances
            prompts: List of PromptModel instances
            generate_archetype: Whether to generate archetype label
            current_timestamp: Optional current timestamp (defaults to now)
            store_in_dbs: Whether to store behaviors/prompts in databases
            
        Returns:
            CoreBehaviorProfile: Complete profile with primary/secondary behaviors
        """
        try:
            if current_timestamp is None:
                current_timestamp = int(time.time())
            
            logger.info(
                f"Starting analysis with new data for user {user_id}: "
                f"{len(behaviors)} behaviors, {len(prompts)} prompts"
            )
            
            # Step 1: Store prompts in MongoDB (normal scenario: prompts are in MongoDB)
            if store_in_dbs:
                logger.info("Step 1: Storing prompts in MongoDB")
                self.mongodb.insert_prompts_bulk(prompts)
            
            # Step 2: Calculate metrics for all behaviors
            logger.info("Step 2: Calculating behavior metrics (BW, ABW)")
            behavior_metrics = self.calculation_engine.calculate_all_metrics_batch(
                behaviors, 
                current_timestamp
            )
            
            # Step 3: Generate embeddings
            logger.info("Step 3: Generating embeddings")
            behavior_texts = [b.behavior_text for b in behaviors]
            embeddings = self.embedding_service.generate_embeddings_for_behaviors(
                behavior_texts
            )
            
            # Step 4: Store behaviors with embeddings in Qdrant (normal scenario: behaviors in Qdrant)
            if store_in_dbs:
                logger.info("Step 4: Storing behaviors with embeddings in Qdrant")
                behavior_ids = [b.observation_id for b in behaviors]
                timestamps = [b.timestamp for b in behaviors]
                
                self.qdrant.insert_embeddings(
                    embeddings=embeddings,
                    behavior_ids=behavior_ids,
                    behavior_texts=behavior_texts,
                    user_id=user_id,
                    timestamps=timestamps
                )
                
                # Step 5: Optionally store behavior metadata in MongoDB (for quick access)
                logger.info("Step 5: Storing behavior metadata in MongoDB")
                self.mongodb.insert_behaviors_bulk(behaviors)
            
            # Step 6: Perform clustering
            logger.info("Step 6: Performing HDBSCAN clustering")
            clustering_result = self.clustering_engine.cluster_behaviors(
                embeddings=embeddings,
                behavior_ids=[b.behavior_id for b in behaviors]
            )
            
            # Step 7-9: Process clusters
            logger.info("Step 7-9: Processing clusters (CBI, canonical, tiers)")
            primary_behaviors, secondary_behaviors, clusters_formed = \
                self._process_clusters(
                    clustering_result,
                    behaviors,
                    behavior_metrics,
                    prompts
                )
            
            # Step 10: Calculate overall statistics
            logger.info("Step 10: Calculating profile statistics")
            time_span_days = self._calculate_time_span(prompts)
            
            statistics = ProfileStatistics(
                total_behaviors_analyzed=len(behaviors),
                clusters_formed=clusters_formed,
                total_prompts_analyzed=len(prompts),
                analysis_time_span_days=time_span_days
            )
            
            # Step 11: Generate archetype (optional)
            archetype = None
            if generate_archetype and (primary_behaviors or secondary_behaviors):
                logger.info("Step 11: Generating behavioral archetype")
                canonical_texts = [
                    b.behavior_text 
                    for b in primary_behaviors + secondary_behaviors
                ]
                archetype = self.archetype_service.generate_archetype(
                    canonical_texts,
                    user_id
                )
            
            # Step 12: Create profile
            profile = CoreBehaviorProfile(
                user_id=user_id,
                generated_at=current_timestamp,
                primary_behaviors=primary_behaviors,
                secondary_behaviors=secondary_behaviors,
                archetype=archetype,
                statistics=statistics
            )
            
            # Step 13: Store profile in MongoDB
            logger.info("Step 13: Storing profile in MongoDB")
            self.mongodb.insert_profile(profile)
            
            logger.info(
                f"Analysis complete for user {user_id}: "
                f"{len(primary_behaviors)} PRIMARY, {len(secondary_behaviors)} SECONDARY"
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error in analysis pipeline: {e}")
            raise
    
    def _construct_behaviors_from_qdrant(
        self, 
        qdrant_behaviors: List[Dict[str, Any]]
    ) -> List[BehaviorObservation]:
        """
        Construct BehaviorObservation instances from Qdrant payload
        Used as fallback when behaviors not in MongoDB
        Maps old field names (behavior_id, created_at) to new schema (observation_id, timestamp)
        
        Args:
            qdrant_behaviors: List of Qdrant point data with payloads
            
        Returns:
            List of BehaviorObservation instances with default values
        """
        behaviors = []
        for qb in qdrant_behaviors:
            payload = qb["payload"]
            # Map old field names to new schema
            observation_id = payload.get("observation_id", payload.get("behavior_id"))
            timestamp = payload.get("timestamp", payload.get("created_at", int(time.time())))
            prompt_ids = payload.get("prompt_history_ids", [])
            prompt_id = prompt_ids[0] if prompt_ids else f"prompt_{timestamp}"
            
            # Create behavior with mapped fields
            behavior = BehaviorObservation(
                observation_id=observation_id,
                behavior_text=payload["behavior_text"],
                credibility=payload.get("credibility", 0.8),
                clarity_score=payload.get("clarity_score", 0.8),
                extraction_confidence=payload.get("extraction_confidence", 0.8),
                timestamp=timestamp,
                prompt_id=prompt_id,
                decay_rate=payload.get("decay_rate", 0.01),
                user_id=payload["user_id"],
                session_id=payload.get("session_id")
            )
            behaviors.append(behavior)
        
        logger.warning(f"Constructed {len(behaviors)} behaviors from Qdrant payload with default values")
        return behaviors
    
    def _process_clusters(
        self,
        clustering_result: Dict[str, Any],
        behaviors: List[BehaviorObservation],
        behavior_metrics: Dict[str, Dict[str, float]],
        prompts: List[PromptModel]
    ) -> tuple[List[CanonicalBehavior], List[CanonicalBehavior], int]:
        """
        Process clustering results to create canonical behaviors with tiers
        
        Returns:
            tuple: (primary_behaviors, secondary_behaviors, num_clusters)
        """
        clusters = clustering_result["clusters"]
        
        # Map behaviors and prompts for quick lookup (handle both old and new field names)
        behavior_map = {b.observation_id: b for b in behaviors}
        prompt_map = {p.prompt_id: p for p in prompts}
        
        primary_behaviors = []
        secondary_behaviors = []
        
        for cluster_id, behavior_ids in clusters.items():
            # Get behaviors in this cluster with their metrics
            cluster_behaviors = []
            for bid in behavior_ids:
                if bid in behavior_metrics:
                    cluster_behaviors.append({
                        "behavior_id": bid,
                        "abw": behavior_metrics[bid]["abw"]
                    })
            
            if not cluster_behaviors:
                continue
            
            # Calculate Cluster CBI
            abw_list = [b["abw"] for b in cluster_behaviors]
            cluster_cbi = self.calculation_engine.calculate_cluster_cbi(abw_list)
            
            # Select canonical behavior
            canonical_id = self.calculation_engine.select_canonical_behavior(
                cluster_behaviors
            )
            canonical_behavior = behavior_map[canonical_id]
            canonical_abw = behavior_metrics[canonical_id]["abw"]
            
            # Assign tier
            tier = self.calculation_engine.assign_tier(cluster_cbi)
            
            # Skip NOISE tier
            if tier == TierEnum.NOISE:
                logger.debug(f"{cluster_id} assigned to NOISE, skipping")
                continue
            
            # Calculate temporal metrics using behavior's actual timeline
            # For BehaviorObservation: use timestamp (single point)
            # For legacy data: use created_at/last_seen if available
            first_seen = getattr(canonical_behavior, 'created_at', canonical_behavior.timestamp)
            last_seen = getattr(canonical_behavior, 'last_seen', canonical_behavior.timestamp)
            
            temporal_span = TemporalSpan(
                first_seen=first_seen,
                last_seen=last_seen,
                days_active=(last_seen - first_seen) / 86400
            )
            
            # Create canonical behavior
            canonical = CanonicalBehavior(
                behavior_id=canonical_id,
                behavior_text=canonical_behavior.behavior_text,
                cluster_id=cluster_id,
                cbi_original=canonical_abw,
                cluster_cbi=cluster_cbi,
                tier=tier,
                temporal_span=temporal_span
            )
            
            # Add to appropriate list
            if tier == TierEnum.PRIMARY:
                primary_behaviors.append(canonical)
            elif tier == TierEnum.SECONDARY:
                secondary_behaviors.append(canonical)
        
        return primary_behaviors, secondary_behaviors, len(clusters)
    
    def _calculate_time_span(self, prompts: List[PromptModel]) -> float:
        """Calculate time span in days from prompts"""
        if not prompts:
            return 0.0
        
        timestamps = [p.timestamp for p in prompts]
        min_time = min(timestamps)
        max_time = max(timestamps)
        
        return (max_time - min_time) / 86400
    
    async def update_behavior_metrics(
        self,
        behavior_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update behavior and recalculate if needed
        
        Args:
            behavior_id: Behavior identifier
            updates: Fields to update
            
        Returns:
            bool: Success status
        """
        try:
            # Update in MongoDB
            success = self.mongodb.update_behavior(behavior_id, updates)
            
            if success:
                logger.info(f"Updated behavior {behavior_id}: {updates}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating behavior: {e}")
            return False
    
    async def assign_archetype_to_profile(
        self,
        user_id: str,
        canonical_behaviors: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Generate and assign archetype to existing profile
        
        Args:
            user_id: User identifier
            canonical_behaviors: Optional list of behavior texts (if not provided, fetches from profile)
            
        Returns:
            str: Generated archetype label or None
        """
        try:
            # If canonical behaviors not provided, fetch from profile
            if canonical_behaviors is None:
                profile_data = self.mongodb.get_profile(user_id)
                if not profile_data:
                    logger.error(f"No profile found for user {user_id}")
                    return None
                
                canonical_behaviors = []
                for behavior in profile_data.get("primary_behaviors", []):
                    canonical_behaviors.append(behavior["behavior_text"])
                for behavior in profile_data.get("secondary_behaviors", []):
                    canonical_behaviors.append(behavior["behavior_text"])
            
            if not canonical_behaviors:
                logger.warning(f"No canonical behaviors for user {user_id}")
                return None
            
            # Generate archetype
            archetype = self.archetype_service.generate_archetype(
                canonical_behaviors,
                user_id
            )
            
            # Update profile
            self.mongodb.update_profile_archetype(user_id, archetype)
            
            logger.info(f"Assigned archetype '{archetype}' to user {user_id}")
            
            return archetype
            
        except Exception as e:
            logger.error(f"Error assigning archetype: {e}")
            return None


# Global analysis pipeline instance
analysis_pipeline = AnalysisPipeline()
