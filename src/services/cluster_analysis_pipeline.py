from typing import List, Dict, Any
import logging
import numpy as np
import time

from src.services.clustering_engine import ClusteringEngine
from src.services.calculation_engine import CalculationEngine
from src.models.schemas import BehaviorObservation, BehaviorCluster, TierEnum

logger = logging.getLogger(__name__)


class ClusterAnalysisPipeline:
    """Cluster-centric pipeline for behavior analysis"""
    
    def __init__(self):
        self.clustering_engine = ClusteringEngine()
        self.calc_engine = CalculationEngine()
    
    def process_behaviors(
        self,
        observations: List[BehaviorObservation],
        user_id: str
    ) -> List[BehaviorCluster]:
        """
        Process observations through cluster-centric pipeline
        
        Steps:
        1. Cluster observations by embedding similarity
        2. Calculate cluster-level metrics
        3. Assign tiers
        4. Generate canonical labels
        
        Args:
            observations: List of BehaviorObservation objects
            user_id: User identifier
            
        Returns:
            List of BehaviorCluster objects
        """
        logger.info(f"Processing {len(observations)} observations for user {user_id}")
        
        if not observations:
            logger.warning("No observations to process")
            return []
        
        # Step 1: Extract embeddings
        embeddings = np.array([obs.embedding for obs in observations if obs.embedding])
        
        if len(embeddings) == 0:
            logger.warning("No valid embeddings found")
            return []
        
        # Step 2: Cluster
        cluster_result = self.clustering_engine.cluster_behaviors(embeddings)
        labels = cluster_result['labels']
        
        # Step 3: Group observations by cluster
        clusters_map: Dict[int, List[BehaviorObservation]] = {}
        for idx, label in enumerate(labels):
            if label == -1:  # Skip noise
                continue
            if label not in clusters_map:
                clusters_map[label] = []
            clusters_map[label].append(observations[idx])
        
        # Step 4: Build cluster objects
        clusters = []
        current_time = int(time.time())
        
        for cluster_id, cluster_obs in clusters_map.items():
            # Calculate metrics
            mean_abw = self._calculate_mean_abw(cluster_obs)
            timestamps = [obs.timestamp for obs in cluster_obs]
            
            cluster_strength = self.calc_engine.calculate_cluster_strength(
                cluster_size=len(cluster_obs),
                mean_abw=mean_abw,
                timestamps=timestamps,
                current_timestamp=current_time
            )
            
            confidence = self.calc_engine.calculate_cluster_confidence(
                observations=cluster_obs,
                cluster_size=len(cluster_obs)
            )
            
            canonical_label = self.calc_engine.select_canonical_label(cluster_obs)
            
            # Temporal tracking
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            days_active = (last_seen - first_seen) / 86400
            
            # Assign tier
            tier = self._assign_tier(cluster_strength)
            
            # Create cluster object
            cluster = BehaviorCluster(
                cluster_id=f"cluster_{cluster_id}",
                user_id=user_id,
                observation_ids=[obs.observation_id for obs in cluster_obs],
                observations=cluster_obs,
                cluster_size=len(cluster_obs),
                canonical_label=canonical_label,
                cluster_strength=cluster_strength,
                confidence=confidence,
                all_prompt_ids=[obs.prompt_id for obs in cluster_obs if obs.prompt_id],
                all_timestamps=timestamps,
                first_seen=first_seen,
                last_seen=last_seen,
                days_active=days_active,
                tier=tier,
                created_at=current_time,
                updated_at=current_time
            )
            
            clusters.append(cluster)
        
        logger.info(f"Created {len(clusters)} clusters")
        return clusters
    
    def _calculate_mean_abw(self, observations: List[BehaviorObservation]) -> float:
        """Calculate mean ABW for observations"""
        abw_values = [obs.abw for obs in observations if obs.abw is not None]
        if not abw_values:
            return 1.0  # Default
        return sum(abw_values) / len(abw_values)
    
    def _assign_tier(self, cluster_strength: float) -> TierEnum:
        """Assign tier based on cluster strength"""
        if cluster_strength >= 0.70:
            return TierEnum.PRIMARY
        elif cluster_strength >= 0.50:
            return TierEnum.SECONDARY
        else:
            return TierEnum.NOISE
