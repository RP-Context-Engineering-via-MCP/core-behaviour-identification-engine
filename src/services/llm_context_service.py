"""
LLM Context Service
Generates behavioral context for LLM prompt injection
Uses strength-based ranking instead of tier labels
"""
from typing import List, Dict, Optional
import logging
from src.models.schemas import BehaviorCluster, TierEnum
from src.database.mongodb_service import mongodb_service

logger = logging.getLogger(__name__)


class LLMContextService:
    """Service for generating LLM-injectable behavioral context"""
    
    @staticmethod
    def generate_llm_context(
        clusters: List[BehaviorCluster],
        archetype: Optional[str] = None,
        min_strength: float = 0.40,
        min_confidence: float = 0.70,
        max_behaviors: int = 5,
        include_variations: bool = True,
        format_style: str = "detailed"
    ) -> str:
        """
        Generate formatted behavioral context for LLM injection
        
        Args:
            clusters: List of behavior clusters
            archetype: User's behavioral archetype
            min_strength: Minimum cluster strength threshold (0-1 scale)
            min_confidence: Minimum confidence threshold (0-1 scale)
            max_behaviors: Maximum number of behaviors to include
            include_variations: Whether to include wording variations
            format_style: 'detailed', 'compact', or 'system_prompt'
            
        Returns:
            Formatted context string ready for LLM injection
        """
        # Filter relevant clusters
        relevant_clusters = [
            c for c in clusters 
            if c.cluster_strength >= min_strength 
            and c.confidence >= min_confidence
            and c.tier != TierEnum.NOISE  # Exclude noise
        ]
        
        # Sort by strength (most dominant first)
        relevant_clusters.sort(key=lambda x: x.cluster_strength, reverse=True)
        
        # Limit to max_behaviors
        top_clusters = relevant_clusters[:max_behaviors]
        
        if not top_clusters:
            return "No significant behavioral patterns detected."
        
        # Generate context based on format style
        if format_style == "system_prompt":
            return LLMContextService._format_system_prompt(top_clusters, archetype, include_variations)
        elif format_style == "compact":
            return LLMContextService._format_compact(top_clusters, archetype)
        else:  # detailed
            return LLMContextService._format_detailed(top_clusters, archetype, include_variations)
    
    @staticmethod
    def _format_detailed(
        clusters: List[BehaviorCluster], 
        archetype: Optional[str],
        include_variations: bool
    ) -> str:
        """Detailed format with all information"""
        parts = []
        
        # Header
        parts.append("# User Behavioral Profile")
        if archetype:
            parts.append(f"Archetype: {archetype}")
        parts.append("")
        
        # Behaviors
        parts.append("## Communication Preferences:")
        parts.append("")
        
        for i, cluster in enumerate(clusters, 1):
            strength_pct = int(cluster.cluster_strength * 100)
            confidence_pct = int(cluster.confidence * 100)
            
            parts.append(
                f"{i}. {cluster.canonical_label} "
                f"(strength: {strength_pct}%, confidence: {confidence_pct}%)"
            )
            
            # Add wording variations for context
            if include_variations and cluster.wording_variations:
                examples = cluster.wording_variations[:3]  # Top 3 variations
                parts.append(f"   Examples: \"{', '.join(examples)}\"")
            
            parts.append("")
        
        return "\n".join(parts)
    
    @staticmethod
    def _format_compact(clusters: List[BehaviorCluster], archetype: Optional[str]) -> str:
        """Compact format for token efficiency"""
        parts = []
        
        if archetype:
            parts.append(f"User Type: {archetype}")
        
        parts.append("Preferences:")
        for cluster in clusters:
            strength_pct = int(cluster.cluster_strength * 100)
            parts.append(f"- {cluster.canonical_label} ({strength_pct}%)")
        
        return "\n".join(parts)
    
    @staticmethod
    def _format_system_prompt(
        clusters: List[BehaviorCluster],
        archetype: Optional[str],
        include_variations: bool
    ) -> str:
        """Format suitable for system prompt injection"""
        parts = []
        
        parts.append("You are assisting a user with the following communication preferences:")
        parts.append("")
        
        for i, cluster in enumerate(clusters, 1):
            strength_pct = int(cluster.cluster_strength * 100)
            
            # Build behavior description
            desc = f"{i}. {cluster.canonical_label} ({strength_pct}% strength)"
            
            # Add variations as usage examples
            if include_variations and cluster.wording_variations:
                examples = cluster.wording_variations[:2]
                desc += f" - Often uses phrases like: \"{examples[0]}\""
                if len(examples) > 1:
                    desc += f", \"{examples[1]}\""
            
            parts.append(desc)
        
        parts.append("")
        parts.append("Adapt your responses to match these preferences while maintaining accuracy and helpfulness.")
        
        return "\n".join(parts)
    
    @staticmethod
    def get_behavior_summary(clusters: List[BehaviorCluster]) -> Dict[str, any]:
        """
        Get statistical summary of behaviors for API response
        
        Returns:
            Dictionary with behavior statistics
        """
        if not clusters:
            return {
                "total_clusters": 0,
                "strong_behaviors": 0,
                "average_strength": 0.0,
                "average_confidence": 0.0
            }
        
        # Filter by strength > 40%
        strong = [c for c in clusters if c.cluster_strength >= 0.40]
        
        avg_strength = sum(c.cluster_strength for c in clusters) / len(clusters)
        avg_confidence = sum(c.confidence for c in clusters) / len(clusters)
        
        return {
            "total_clusters": len(clusters),
            "strong_behaviors": len(strong),
            "average_strength": round(avg_strength, 3),
            "average_confidence": round(avg_confidence, 3),
            "top_behavior": clusters[0].canonical_label if clusters else None
        }


# Singleton instance
llm_context_service = LLMContextService()


async def generate_llm_context(
    user_id: str,
    min_strength: float = 30.0,  # 30% minimum strength
    min_confidence: float = 0.40,  # 40% minimum confidence
    max_behaviors: int = 5,
    include_archetype: bool = True
) -> Optional[Dict]:
    """
    Generate LLM context for a user from their profile
    
    Args:
        user_id: User identifier
        min_strength: Minimum cluster strength percentage (0-100)
        min_confidence: Minimum confidence score (0-1.0)
        max_behaviors: Maximum number of behaviors to include
        include_archetype: Whether to include archetype description
    
    Returns:
        Dict with formatted context string and metadata, or None if no profile
    """
    try:
        # Fetch user profile from MongoDB
        profile_data = mongodb_service.get_profile(user_id)
        
        if not profile_data:
            return None
        
        # Convert clusters to BehaviorCluster objects
        clusters = []
        for cluster_data in profile_data.get("behavior_clusters", []):
            cluster = BehaviorCluster(**cluster_data)
            clusters.append(cluster)
        
        # Get archetype
        archetype_value = profile_data.get("archetype")
        if include_archetype:
            # Handle both string and dict formats
            if isinstance(archetype_value, dict):
                archetype = archetype_value.get("archetype_name")
            elif isinstance(archetype_value, str):
                archetype = archetype_value
            else:
                archetype = None
        else:
            archetype = None
        
        # Convert percentage to 0-1 scale for internal processing
        min_strength_ratio = min_strength / 100.0
        
        # Generate context using the service
        context_string = llm_context_service.generate_llm_context(
            clusters=clusters,
            archetype=archetype,
            min_strength=min_strength_ratio,
            min_confidence=min_confidence,
            max_behaviors=max_behaviors,
            include_variations=True,
            format_style="detailed"
        )
        
        # Get summary stats
        summary = llm_context_service.get_behavior_summary(clusters)
        
        return {
            "user_id": user_id,
            "context": context_string,
            "metadata": {
                "total_clusters": len(clusters),
                "included_behaviors": min(max_behaviors, len([c for c in clusters if c.cluster_strength >= min_strength_ratio and c.confidence >= min_confidence])),
                "archetype": archetype,
                "filters": {
                    "min_strength": min_strength,
                    "min_confidence": min_confidence,
                    "max_behaviors": max_behaviors
                },
                "summary": summary
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating LLM context for user {user_id}: {e}")
        raise
