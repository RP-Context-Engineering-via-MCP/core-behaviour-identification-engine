"""
Calculation Engine for CBIE System
Implements cluster-centric formulas from MVP documentation

ACTIVE METHODS:
  ✅ calculate_cluster_strength() - Main cluster scoring
  ✅ calculate_cluster_confidence() - Confidence metrics
  ✅ select_canonical_label() - Label selection
  ✅ _calculate_recency_factor() - Temporal decay
"""
import math
from typing import List, Dict, Any, Optional
import time
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class CalculationEngine:
    """Engine for calculating cluster-level behavior metrics"""
    
    def __init__(self):
        # Threshold parameters from settings
        self.primary_threshold = settings.primary_threshold  # 1.0
        self.secondary_threshold = settings.secondary_threshold  # 0.7
    
    def calculate_behavior_metrics(
        self,
        behavior: Any,
        current_timestamp: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate quality score for a behavior observation (used by cluster pipeline)
        
        Uses simple average of quality metrics without arbitrary exponential parameters.
        
        Args:
            behavior: BehaviorObservation instance
            current_timestamp: Current Unix timestamp (defaults to now)
            
        Returns:
            dict: Contains 'bw', 'abw', 'days_active' (bw=abw=quality_score for compatibility)
        """
        # Simple quality score: arithmetic mean of the three quality dimensions
        # No arbitrary alpha/beta/gamma parameters
        quality_score = (
            behavior.credibility + 
            behavior.clarity_score + 
            behavior.extraction_confidence
        ) / 3.0
        
        behavior_id = getattr(behavior, 'observation_id', getattr(behavior, 'behavior_id', 'unknown'))
        
        # Return quality_score for both bw and abw (no complex weighting)
        return {
            "behavior_id": behavior_id,
            "bw": quality_score,
            "abw": quality_score,
            "days_active": 0.0
        }
    
    def calculate_cluster_strength(
        self,
        cluster_size: int,
        mean_abw: float,
        timestamps: List[int],
        current_timestamp: Optional[int] = None
    ) -> float:
        """
        Calculate cluster strength (REPLACES naive ABW averaging)
        
        Formula: cluster_strength = normalized(log(cluster_size + 1) * mean(ABW) * recency_factor)
        
        Normalization ensures output is in [0, 1] range for stable threshold comparison.
        
        THRESHOLD GUIDE (after normalization):
        - 3 observations (high quality): ~0.52 → SECONDARY
        - 8 observations (high quality): ~0.73 → PRIMARY (if threshold is 0.70)
        - 15 observations (high quality): ~0.82 → Strong PRIMARY
        
        Args:
            cluster_size: Number of observations in cluster
            mean_abw: Mean ABW of all observations
            timestamps: All observation timestamps
            current_timestamp: Current time (defaults to now)
            
        Returns:
            float: Normalized cluster strength score (0-1)
        """
        if current_timestamp is None:
            current_timestamp = int(time.time())
        
        # Logarithmic size bonus (diminishing returns)
        size_factor = math.log(cluster_size + 1)
        
        # Calculate recency factor (weighted decay)
        recency_factor = self._calculate_recency_factor(timestamps, current_timestamp)
        
        # Raw strength (unbounded)
        raw_strength = size_factor * mean_abw * recency_factor
        
        # Normalize using sigmoid-like function: x / (1 + x)
        # This maps: 0→0, 0.5→0.33, 1→0.5, 2→0.67, 3→0.75, 5→0.83
        normalized_strength = raw_strength / (1 + raw_strength)
        
        logger.debug(
            f"Cluster strength: log({cluster_size}+1)={size_factor:.2f} * ABW={mean_abw:.2f} * "
            f"Recency={recency_factor:.2f} = Raw={raw_strength:.2f} → Normalized={normalized_strength:.4f}"
        )
        
        return round(normalized_strength, 4)
    
    def _calculate_recency_factor(
        self,
        timestamps: List[int],
        current_timestamp: int
    ) -> float:
        """
        Calculate recency factor for cluster strength
        
        More recent observations are weighted higher.
        Uses exponential decay based on time since observation.
        
        Args:
            timestamps: List of observation timestamps
            current_timestamp: Current time
            
        Returns:
            float: Recency factor (0-1)
        """
        if not timestamps:
            return 0.0
        
        # Calculate recency without arbitrary decay rates
        # Use inverse of days since (more recent = higher weight)
        # Normalize by max days to get 0-1 range
        days_since = [(current_timestamp - ts) / 86400 for ts in timestamps]
        max_days = max(days_since) if days_since else 1
        
        # Weight by relative recency: (max_days - days) / max_days
        # Recent observations get weight closer to 1, old ones closer to 0
        if max_days > 0:
            weights = [(max_days - days) / max_days for days in days_since]
        else:
            weights = [1.0] * len(timestamps)  # All same time = all weight 1
        
        # Return average weight
        recency_factor = sum(weights) / len(weights)
        
        return recency_factor
    
    def calculate_cluster_confidence(
        self,
        intra_cluster_distances: List[float],
        cluster_size: int,
        clarity_scores: List[float],
        timestamps: List[int]
    ) -> Dict[str, float]:
        """
        Calculate cluster-level confidence using Multiplicative Model (NO magic weights)
        
        Confidence = Consistency × Reinforcement (with optional clarity bonus)
        
        This requires BOTH high consistency AND reasonable sample size for high confidence.
        No arbitrary 0.4/0.4/0.2 weights needed.
        
        Args:
            intra_cluster_distances: Distance of each member from centroid
            cluster_size: Number of observations
            clarity_scores: Clarity score of each observation
            timestamps: Timestamp of each observation (for trend analysis)
            
        Returns:
            dict: Contains 'confidence', 'consistency_score', 'reinforcement_score', 'clarity_trend'
        """
        # 1. Consistency score (inverse of mean distance)
        # Low distance = high similarity = high confidence
        mean_distance = sum(intra_cluster_distances) / len(intra_cluster_distances) if intra_cluster_distances else 0
        consistency_score = 1.0 / (1.0 + mean_distance)  # Maps [0, inf) to (0, 1]
        
        # 2. Reinforcement score (logarithmic in cluster size)
        # Using log10 so 10 observations = 1.0 score
        reinforcement_score = math.log10(cluster_size + 1)
        reinforcement_score = min(1.0, reinforcement_score)  # Cap at 1.0
        
        # 3. Clarity trend (for reporting, not in main formula)
        clarity_trend = 0.0
        if len(timestamps) >= 2:
            # Pair timestamps with clarity scores and sort
            time_clarity_pairs = sorted(zip(timestamps, clarity_scores))
            sorted_clarity = [c for _, c in time_clarity_pairs]
            
            # Simple trend: compare first half to second half
            mid = len(sorted_clarity) // 2
            first_half_avg = sum(sorted_clarity[:mid]) / mid if mid > 0 else sorted_clarity[0]
            second_half_avg = sum(sorted_clarity[mid:]) / (len(sorted_clarity) - mid)
            
            # Range: -1 (degrading) to +1 (improving)
            clarity_trend = second_half_avg - first_half_avg
        
        # Multiplicative model: Requires BOTH consistency AND reinforcement to be high
        confidence = consistency_score * reinforcement_score
        
        # Apply clarity trend directly (no arbitrary percentage)
        # Positive trend increases confidence, negative decreases
        # Since clarity_trend is in range [-1, 1], this naturally scales confidence
        if clarity_trend != 0:
            confidence = confidence * (1.0 + clarity_trend)
        
        # Cap at 1.0
        confidence = min(1.0, confidence)
        
        logger.debug(
            f"Cluster confidence = {confidence:.4f} "
            f"(consistency={consistency_score:.4f} × reinforcement={reinforcement_score:.4f}, "
            f"clarity_trend={clarity_trend:.4f})"
        )
        
        return {
            "confidence": round(confidence, 4),
            "consistency_score": round(consistency_score, 4),
            "reinforcement_score": round(reinforcement_score, 4),
            "clarity_trend": round(clarity_trend, 4)
        }
    
    def select_canonical_label(
        self,
        observations: List[Any],  # List of BehaviorObservation
        use_llm: bool = True
    ) -> str:
        """
        Select canonical label for display (NOT for scoring)
        
        Strategy:
        1. If multiple observations and LLM available: Use LLM to generate best label
        2. Fallback: Return longest/most descriptive text
        
        This is ONLY for UI display - never use for confidence or scoring.
        
        Args:
            observations: List of BehaviorObservation objects
            use_llm: Whether to use LLM for label generation (default: True)
            
        Returns:
            str: Canonical behavior text label
        """
        if not observations:
            raise ValueError("Cannot select canonical from empty cluster")
        
        # Extract behavior texts
        behavior_texts = [obs.behavior_text for obs in observations]
        
        # If only one observation, just return it
        if len(behavior_texts) == 1:
            return behavior_texts[0]
        
        # Try LLM-based label generation for multi-observation clusters
        if use_llm and len(behavior_texts) > 1:
            try:
                from src.services.archetype_service import archetype_service
                label = archetype_service.generate_concise_label(behavior_texts)
                logger.debug(f"Generated LLM label: '{label}' from {len(behavior_texts)} observations")
                return label
            except Exception as e:
                logger.warning(f"LLM label generation failed: {e}. Using fallback.")
        
        # Fallback: Return longest text (usually most descriptive)
        longest_text = max(behavior_texts, key=len)
        logger.debug(f"Using fallback label (longest): '{longest_text}'")
        return longest_text


# Global calculation engine instance
calculation_engine = CalculationEngine()
