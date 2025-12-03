from typing import List, Dict, Any
import logging

from src.models.schemas import BehaviorCluster, TierEnum

logger = logging.getLogger(__name__)


class ArchetypeService:
    """Service for grouping clusters into user archetypes"""
    
    def __init__(self):
        pass
    
    def generate_archetypes(
        self,
        clusters: List[BehaviorCluster],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Group behavior clusters into user archetypes
        
        Args:
            clusters: List of BehaviorCluster objects
            user_id: User identifier
            
        Returns:
            Dict containing archetype information
        """
        logger.info(f"Generating archetypes for user {user_id} from {len(clusters)} clusters")
        
        # Group by tier
        primary_behaviors = [c for c in clusters if c.tier == TierEnum.PRIMARY]
        secondary_behaviors = [c for c in clusters if c.tier == TierEnum.SECONDARY]
        
        # Generate archetype summary
        archetype = {
            "user_id": user_id,
            "total_clusters": len(clusters),
            "primary_behaviors": len(primary_behaviors),
            "secondary_behaviors": len(secondary_behaviors),
            "dominant_patterns": [c.canonical_label for c in primary_behaviors[:5]],
            "confidence_score": self._calculate_archetype_confidence(clusters)
        }
        
        logger.info(
            f"Generated archetype: {len(primary_behaviors)} primary, "
            f"{len(secondary_behaviors)} secondary behaviors"
        )
        
        return archetype
    
    def _calculate_archetype_confidence(self, clusters: List[BehaviorCluster]) -> float:
        """Calculate overall confidence for archetype"""
        if not clusters:
            return 0.0
        
        # Average confidence weighted by cluster strength
        total_weight = sum(c.cluster_strength for c in clusters)
        if total_weight == 0:
            return 0.0
        
        weighted_confidence = sum(
            c.confidence * c.cluster_strength for c in clusters
        ) / total_weight
        
        return round(weighted_confidence, 4)
