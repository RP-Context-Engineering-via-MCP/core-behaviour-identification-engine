"""
CLUSTER-CENTRIC Analysis Pipeline for CBIE System
This is the CORRECT implementation where CLUSTERS are the primary entity.

Key differences from old pipeline:
1. Clusters are processed first, behaviors second
2. ALL observations in clusters are preserved and used
3. Scoring is based on cluster strength, not canonical behavior
4. Confidence comes from cluster consistency, not individual extraction_confidence
"""
from typing import List, Dict, Any, Optional
import time
import logging
import numpy as np

from src.models.schemas import (
    BehaviorObservation,
    BehaviorCluster,
    PromptModel,
    CoreBehaviorProfile,
    ProfileStatistics,
    TierEnum
)
from src.services.calculation_engine import calculation_engine
from src.services.embedding_service import embedding_service
from src.services.clustering_engine import clustering_engine
from src.services.archetype_service import archetype_service
from src.database.mongodb_service import mongodb_service
from src.database.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


class ClusterAnalysisPipeline:
    """
    Cluster-centric analysis pipeline
    Clusters are the PRIMARY entity - observations are aggregated within clusters
    """
    
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
        Analyze behaviors from Qdrant storage using cluster-centric approach
        
        This is the main entry point for production analysis.
        Fetches behaviors from Qdrant and prompts from MongoDB, then runs cluster analysis.
        
        Args:
            user_id: User identifier
            generate_archetype: Whether to generate archetype
            current_timestamp: Optional current timestamp
            
        Returns:
            CoreBehaviorProfile with behavior_clusters
        """
        logger.info(f"Fetching data from storage for user {user_id}")
        
        # Fetch behaviors from Qdrant (source of truth)
        qdrant_behaviors = self.qdrant.get_embeddings_by_user(user_id)
        if not qdrant_behaviors:
            raise ValueError(f"No behaviors found in Qdrant for user {user_id}")
        
        # Construct BehaviorObservation objects from Qdrant payload
        observations = []
        for qb in qdrant_behaviors:
            payload = qb["payload"]
            obs_id = payload.get("observation_id", payload.get("behavior_id"))
            timestamp = payload.get("timestamp", payload.get("created_at", int(time.time())))
            prompt_ids = payload.get("prompt_history_ids", [])
            prompt_id = prompt_ids[0] if prompt_ids else f"prompt_{timestamp}"
            
            obs = BehaviorObservation(
                observation_id=obs_id,
                behavior_text=payload["behavior_text"],
                embedding=qb["vector"],  # Include embedding
                credibility=payload.get("credibility", 0.8),
                clarity_score=payload.get("clarity_score", 0.8),
                extraction_confidence=payload.get("extraction_confidence", 0.8),
                timestamp=timestamp,
                prompt_id=prompt_id,
                decay_rate=payload.get("decay_rate", 0.01),
                user_id=payload["user_id"],
                session_id=payload.get("session_id")
            )
            observations.append(obs)
        
        # Fetch prompts from MongoDB
        prompts_data = self.mongodb.get_prompts_by_user(user_id)
        prompts = [PromptModel(**p) for p in prompts_data]
        
        logger.info(f"Loaded {len(observations)} observations and {len(prompts)} prompts from storage")
        
        # Run cluster analysis (skip storing observations - already in Qdrant, but STORE PROFILE)
        return await self.analyze_observations(
            user_id=user_id,
            observations=observations,
            prompts=prompts,
            generate_archetype=generate_archetype,
            current_timestamp=current_timestamp,
            store_in_dbs=True,  # Store profile, but observations already exist in Qdrant
            skip_observation_storage=True  # Flag to skip re-storing observations
        )
    
    async def analyze_observations(
        self,
        user_id: str,
        observations: List[BehaviorObservation],
        prompts: List[PromptModel],
        generate_archetype: bool = True,
        current_timestamp: Optional[int] = None,
        store_in_dbs: bool = True,
        skip_observation_storage: bool = False
    ) -> CoreBehaviorProfile:
        """
        CLUSTER-CENTRIC analysis pipeline
        
        Pipeline steps:
        1. Calculate BW and ABW for each observation
        2. Generate embeddings for observations
        3. Perform HDBSCAN clustering
        4. FOR EACH CLUSTER (primary loop):
           a. Aggregate ALL observations in cluster
           b. Calculate cluster strength (log(size) * mean(ABW) * recency)
           c. Calculate cluster confidence (consistency, reinforcement, clarity_trend)
           d. Select canonical label (UI only - NOT for scoring)
           e. Build BehaviorCluster object with ALL observations
        5. Assign tiers based on cluster_strength
        6. Generate archetype from clusters (optional)
        7. Store clusters in database
        8. Return CoreBehaviorProfile with behavior_clusters
        
        Args:
            user_id: User identifier
            observations: List of BehaviorObservation instances
            prompts: List of PromptModel instances
            generate_archetype: Whether to generate archetype
            current_timestamp: Optional current timestamp
            store_in_dbs: Whether to store in databases
            
        Returns:
            CoreBehaviorProfile with behavior_clusters populated
        """
        try:
            if current_timestamp is None:
                current_timestamp = int(time.time())
            
            logger.info(
                f"Starting CLUSTER-CENTRIC analysis for user {user_id}: "
                f"{len(observations)} observations, {len(prompts)} prompts"
            )
            
            # Step 1: Calculate metrics for all observations
            logger.info("Step 1: Calculating observation metrics (BW, ABW)")
            observation_metrics = {}
            for obs in observations:
                metrics = self.calculation_engine.calculate_behavior_metrics(obs, current_timestamp)
                observation_metrics[obs.observation_id] = metrics
                # Store calculated metrics back into observation
                obs.bw = metrics["bw"]
                obs.abw = metrics["abw"]
            
            # Step 2: Generate embeddings (ONLY if they don't already exist)
            # NOTE: When called from analyze_behaviors_from_storage(), embeddings are already
            # loaded from Qdrant and don't need regeneration. This saves API calls and time.
            logger.info("Step 2: Checking/generating embeddings")
            
            # Check which observations need embeddings
            observations_needing_embeddings = []
            observations_with_embeddings = []
            
            for obs in observations:
                if obs.embedding is None or len(obs.embedding) == 0:
                    observations_needing_embeddings.append(obs)
                else:
                    observations_with_embeddings.append(obs)
            
            # Only generate embeddings for observations that need them
            if observations_needing_embeddings:
                logger.info(f"Generating embeddings for {len(observations_needing_embeddings)} observations without embeddings")
                observation_texts = [obs.behavior_text for obs in observations_needing_embeddings]
                new_embeddings = self.embedding_service.generate_embeddings_for_behaviors(observation_texts)
                
                # Store newly generated embeddings
                for obs, emb in zip(observations_needing_embeddings, new_embeddings):
                    obs.embedding = emb
            else:
                logger.info("All observations already have embeddings (loaded from Qdrant or provided)")
            
            # OLD CODE - Always regenerated embeddings (WASTEFUL, now commented out)
            # logger.info("Step 2: Generating embeddings")
            # observation_texts = [obs.behavior_text for obs in observations]
            # embeddings = self.embedding_service.generate_embeddings_for_behaviors(observation_texts)
            # 
            # # Store embeddings in observations
            # for obs, emb in zip(observations, embeddings):
            #     obs.embedding = emb  # This overwrote embeddings from Qdrant unnecessarily
            
            # Step 3: Extract embeddings for clustering
            # Now that we've ensured all observations have embeddings, extract them
            logger.info("Step 3: Extracting embeddings for clustering")
            embeddings = [obs.embedding for obs in observations]
            
            # Step 3.5: Perform clustering
            logger.info("Step 3.5: Performing HDBSCAN clustering")
            observation_ids = [obs.observation_id for obs in observations]
            clustering_result = self.clustering_engine.cluster_behaviors(embeddings, observation_ids)
            
            # Step 4: Process clusters (THIS IS THE MAIN LOOP)
            logger.info(f"Step 4: Processing {clustering_result['num_clusters']} clusters")
            behavior_clusters = self._build_behavior_clusters(
                clustering_result,
                observations,
                observation_metrics,
                prompts,
                user_id,
                current_timestamp
            )
            
            # Step 5: Assign tiers based on cluster_strength
            logger.info("Step 5: Assigning tiers")
            for cluster in behavior_clusters:
                cluster.tier = self._assign_tier_by_strength(cluster.cluster_strength)
            
            # Step 6: Store in databases (if requested)
            if store_in_dbs and not skip_observation_storage:
                logger.info("Step 6: Storing observations and clusters in databases")
                # Store prompts in MongoDB
                self.mongodb.insert_prompts_bulk(prompts)
                
                # Store observations in Qdrant
                for obs in observations:
                    self.qdrant.insert_behavior(
                        user_id=user_id,
                        behavior_id=obs.observation_id,
                        behavior_text=obs.behavior_text,
                        embedding=obs.embedding,
                        metadata={
                            "credibility": obs.credibility,
                            "clarity_score": obs.clarity_score,
                            "extraction_confidence": obs.extraction_confidence,
                            "timestamp": obs.timestamp,
                            "prompt_id": obs.prompt_id,
                            "bw": obs.bw,
                            "abw": obs.abw
                        }
                    )
                
                # Store clusters in MongoDB
                for cluster in behavior_clusters:
                    self.mongodb.insert_cluster(cluster)
            elif skip_observation_storage:
                logger.info("Step 6: Skipping observation storage (already in Qdrant)")
            
            # Step 7: Generate archetype (optional)
            archetype = None
            if generate_archetype and behavior_clusters:
                logger.info("Step 7: Generating archetype")
                canonical_labels = [c.canonical_label for c in behavior_clusters if c.tier != TierEnum.NOISE]
                if canonical_labels:
                    archetype = self.archetype_service.generate_archetype(canonical_labels, user_id)
            
            # Step 8: Calculate statistics
            time_span_days = self._calculate_time_span(prompts)
            statistics = ProfileStatistics(
                total_behaviors_analyzed=len(observations),
                clusters_formed=len(behavior_clusters),
                total_prompts_analyzed=len(prompts),
                analysis_time_span_days=time_span_days
            )
            
            # Step 9: Create profile
            profile = CoreBehaviorProfile(
                user_id=user_id,
                generated_at=current_timestamp,
                behavior_clusters=behavior_clusters,
                primary_behaviors=[],  # Deprecated
                secondary_behaviors=[],  # Deprecated
                archetype=archetype,
                statistics=statistics
            )
            
            # Step 10: Store profile (only if requested)
            if store_in_dbs:
                logger.info("Step 10: Storing profile in MongoDB")
                self.mongodb.insert_profile(profile)
            else:
                logger.info("Step 10: Skipping database storage (store_in_dbs=False)")
            
            logger.info(
                f"Cluster-centric analysis complete: "
                f"{len([c for c in behavior_clusters if c.tier == TierEnum.PRIMARY])} PRIMARY, "
                f"{len([c for c in behavior_clusters if c.tier == TierEnum.SECONDARY])} SECONDARY clusters"
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Error in cluster-centric analysis pipeline: {e}")
            raise
    
    def _build_behavior_clusters(
        self,
        clustering_result: Dict[str, Any],
        observations: List[BehaviorObservation],
        observation_metrics: Dict[str, Dict[str, float]],
        prompts: List[PromptModel],
        user_id: str,
        current_timestamp: int
    ) -> List[BehaviorCluster]:
        """
        Build BehaviorCluster objects from clustering results
        This is where the REAL work happens - aggregating observations into clusters
        """
        clusters = clustering_result["clusters"]
        cluster_centroids = clustering_result["cluster_centroids"]
        intra_cluster_distances = clustering_result["intra_cluster_distances"]
        cluster_embeddings = clustering_result["cluster_embeddings"]
        
        # Map observations by ID for quick lookup
        obs_map = {obs.observation_id: obs for obs in observations}
        
        behavior_clusters = []
        
        for cluster_id, observation_ids in clusters.items():
            # Get ALL observations in this cluster (NEVER discard)
            cluster_observations = [obs_map[oid] for oid in observation_ids if oid in obs_map]
            
            if not cluster_observations:
                continue
            
            # Aggregate evidence from ALL observations
            all_prompt_ids = []
            all_timestamps = []
            wording_variations = []
            clarity_scores = []
            abw_values = []
            
            for obs in cluster_observations:
                all_prompt_ids.append(obs.prompt_id)
                all_timestamps.append(obs.timestamp)
                wording_variations.append(obs.behavior_text)
                clarity_scores.append(obs.clarity_score)
                if obs.observation_id in observation_metrics:
                    abw_values.append(observation_metrics[obs.observation_id]["abw"])
            
            # Calculate cluster metrics
            cluster_size = len(cluster_observations)
            mean_abw = sum(abw_values) / len(abw_values) if abw_values else 0.0
            
            # Calculate cluster strength (log(size) * mean_abw * recency)
            cluster_strength = self.calculation_engine.calculate_cluster_strength(
                cluster_size=cluster_size,
                mean_abw=mean_abw,
                timestamps=all_timestamps,
                current_timestamp=current_timestamp
            )
            
            # Calculate cluster confidence (consistency, reinforcement, clarity_trend)
            distances = intra_cluster_distances[cluster_id]["all_distances"]
            confidence_metrics = self.calculation_engine.calculate_cluster_confidence(
                intra_cluster_distances=distances,
                cluster_size=cluster_size,
                clarity_scores=clarity_scores,
                timestamps=all_timestamps
            )
            
            # Select canonical label (UI only - NOT for scoring)
            # Now uses LLM-based label generation for better representation
            canonical_label = self.calculation_engine.select_canonical_label(
                observations=cluster_observations,
                use_llm=True
            )
            
            # Temporal metrics
            first_seen = min(all_timestamps)
            last_seen = max(all_timestamps)
            days_active = (last_seen - first_seen) / 86400
            
            # Generate descriptive cluster name using LLM
            cluster_name = self.archetype_service.generate_cluster_name(
                wording_variations=wording_variations,
                cluster_size=cluster_size,
                tier="UNKNOWN"  # Tier assigned later
            )
            
            # Get centroid for storage (optional field)
            centroid = cluster_centroids.get(cluster_id)
            
            # Build BehaviorCluster
            behavior_cluster = BehaviorCluster(
                cluster_id=cluster_id,
                user_id=user_id,
                observation_ids=observation_ids,
                observations=cluster_observations,
                centroid_embedding=centroid,
                cluster_size=cluster_size,
                canonical_label=canonical_label,
                canonical_observation_id=None,  # No longer using single observation ID
                cluster_name=cluster_name,
                cluster_strength=cluster_strength,
                confidence=confidence_metrics["confidence"],
                all_prompt_ids=all_prompt_ids,
                all_timestamps=all_timestamps,
                wording_variations=wording_variations,
                first_seen=first_seen,
                last_seen=last_seen,
                days_active=days_active,
                tier=TierEnum.NOISE,  # Will be assigned later
                created_at=current_timestamp,
                updated_at=current_timestamp,
                consistency_score=confidence_metrics["consistency_score"],
                reinforcement_score=confidence_metrics["reinforcement_score"],
                clarity_trend=confidence_metrics["clarity_trend"],
                mean_abw=mean_abw,
                recency_factor=self.calculation_engine._calculate_recency_factor(all_timestamps, current_timestamp)
            )
            
            behavior_clusters.append(behavior_cluster)
        
        logger.info(f"Built {len(behavior_clusters)} behavior clusters")
        return behavior_clusters
    
    def _assign_tier_by_strength(self, cluster_strength: float) -> TierEnum:
        """
        Assign tier based on cluster_strength (NOT cluster CBI)
        
        New thresholds (need tuning based on log scaling):
        - PRIMARY: strength >= 0.8
        - SECONDARY: 0.4 <= strength < 0.8
        - NOISE: strength < 0.4
        """
        # TODO: These thresholds need empirical tuning
        # They differ from old CBI thresholds because strength uses log(size)
        if cluster_strength >= 0.8:
            return TierEnum.PRIMARY
        elif cluster_strength >= 0.4:
            return TierEnum.SECONDARY
        else:
            return TierEnum.NOISE
    
    def _calculate_time_span(self, prompts: List[PromptModel]) -> float:
        """Calculate time span in days from prompts"""
        if not prompts:
            return 0.0
        
        timestamps = [p.timestamp for p in prompts]
        min_time = min(timestamps)
        max_time = max(timestamps)
        
        return (max_time - min_time) / 86400


# Global cluster-centric pipeline instance
cluster_analysis_pipeline = ClusterAnalysisPipeline()
