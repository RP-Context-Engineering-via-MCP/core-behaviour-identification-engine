"""
Calculation Engine for CBIE System
Implements all formulas from MVP documentation

⚠️ IMPORTANT: Some methods are DEPRECATED (marked with ⚠️ warnings)
These were used in the old observation-centric pipeline.

ACTIVE METHODS (used in cluster-centric pipeline):
  ✅ calculate_cluster_strength() - Main cluster scoring
  ✅ calculate_cluster_confidence() - Confidence metrics
  ✅ select_canonical_label() - Label selection
  ✅ calculate_recency_factor() - Temporal decay

DEPRECATED METHODS (not used, kept for reference):
  ❌ calculate_behavior_weight() - Old BW formula
  ❌ calculate_adjusted_behavior_weight() - Old ABW formula
  ❌ calculate_cluster_cbi() - Old CBI formula
  ❌ select_canonical_behavior() - Old selection method
  ❌ assign_tier() - Old tier assignment
  ❌ calculate_temporal_metrics() - Old temporal calc
"""
import math
from typing import List, Dict, Any, Optional
import time
import logging
import numpy as np

from src.config import settings
from src.models.schemas import BehaviorObservation, TemporalSpan, TierEnum

logger = logging.getLogger(__name__)


class CalculationEngine:
    """Engine for calculating behavior weights and metrics"""
    
    def __init__(self):
        # Formula parameters from settings
        self.alpha = settings.alpha  # 0.35
        self.beta = settings.beta    # 0.40
        self.gamma = settings.gamma  # 0.25
        self.reinforcement_multiplier = settings.reinforcement_multiplier  # 0.01
        self.primary_threshold = settings.primary_threshold  # 1.0
        self.secondary_threshold = settings.secondary_threshold  # 0.7
    
    def calculate_behavior_weight(
        self,
        credibility: float,
        clarity_score: float,
        extraction_confidence: float
    ) -> float:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Calculate Behavior Weight (BW)
        
        Formula: BW = credibility^α × clarity_score^β × extraction_confidence^γ
        
        STATUS: Legacy method from observation-centric approach.
        The cluster pipeline uses direct credibility scoring instead.
        
        Args:
            credibility: Trustworthiness (0-1)
            clarity_score: Explicitness (0-1)
            extraction_confidence: Model confidence (0-1)
            
        Returns:
            float: Behavior Weight
        """
        bw = (
            math.pow(credibility, self.alpha) *
            math.pow(clarity_score, self.beta) *
            math.pow(extraction_confidence, self.gamma)
        )
        
        logger.debug(
            f"BW = {credibility}^{self.alpha} × {clarity_score}^{self.beta} × "
            f"{extraction_confidence}^{self.gamma} = {bw:.6f}"
        )
        
        return bw
    
    def calculate_adjusted_behavior_weight(
        self,
        behavior_weight: float,
        reinforcement_count: int,
        decay_rate: float,
        days_since_last_seen: float
    ) -> float:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Calculate Adjusted Behavior Weight (ABW)
        
        Formula: ABW = BW × (1 + reinforcement_count × r) × e^(-decay_rate × days_since_last_seen)
        
        STATUS: Legacy method from observation-centric approach.
        The cluster pipeline uses direct temporal decay calculation instead.
        
        Args:
            behavior_weight: Base behavior weight (BW)
            reinforcement_count: Number of reinforcements
            decay_rate: Decay rate for this behavior
            days_since_last_seen: Days since behavior was last observed
            
        Returns:
            float: Adjusted Behavior Weight
        """
        reinforcement_factor = 1 + (reinforcement_count * self.reinforcement_multiplier)
        decay_factor = math.exp(-decay_rate * days_since_last_seen)
        
        abw = behavior_weight * reinforcement_factor * decay_factor
        
        logger.debug(
            f"ABW = {behavior_weight:.6f} × (1 + {reinforcement_count} × {self.reinforcement_multiplier}) × "
            f"e^(-{decay_rate} × {days_since_last_seen}) = {abw:.6f}"
        )
        
        return abw
    
    def calculate_days_since_last_seen(
        self,
        last_seen_timestamp: int,
        current_timestamp: Optional[int] = None
    ) -> float:
        """
        Calculate days since behavior was last seen
        
        Args:
            last_seen_timestamp: Unix timestamp of last observation
            current_timestamp: Current Unix timestamp (defaults to now)
            
        Returns:
            float: Days since last seen
        """
        if current_timestamp is None:
            current_timestamp = int(time.time())
        
        days = (current_timestamp - last_seen_timestamp) / 86400
        return max(0.0, days)  # Ensure non-negative
    
    def calculate_behavior_metrics(
        self,
        behavior: BehaviorObservation,
        current_timestamp: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate both BW and ABW for a behavior observation
        
        Args:
            behavior: BehaviorObservation instance
            current_timestamp: Current Unix timestamp (defaults to now). 
                              For historical data, this parameter is ignored and 
                              the observation's timeline is used.
            
        Returns:
            dict: Contains 'bw', 'abw', 'days_active'
        """
        # Calculate BW
        bw = self.calculate_behavior_weight(
            behavior.credibility,
            behavior.clarity_score,
            behavior.extraction_confidence
        )
        
        # Calculate days active
        # For BehaviorObservation: timestamp is single point, so days_active = 0
        # For legacy BehaviorModel: use (last_seen - created_at)
        if hasattr(behavior, 'last_seen') and hasattr(behavior, 'created_at'):
            # Legacy BehaviorModel
            days_active = (behavior.last_seen - behavior.created_at) / 86400
        else:
            # BehaviorObservation - single timestamp
            days_active = 0.0
        
        days_active = max(0.0, days_active)  # Ensure non-negative
        
        # Calculate ABW
        # For observations, reinforcement_count doesn't exist, use 1
        reinforcement_count = getattr(behavior, 'reinforcement_count', 1)
        
        abw = self.calculate_adjusted_behavior_weight(
            bw,
            reinforcement_count,
            behavior.decay_rate,
            days_active
        )
        
        # Use observation_id if available, otherwise behavior_id
        behavior_id = getattr(behavior, 'observation_id', getattr(behavior, 'behavior_id', 'unknown'))
        
        return {
            "behavior_id": behavior_id,
            "bw": bw,
            "abw": abw,
            "days_active": days_active
        }
    
    def calculate_cluster_cbi(self, abw_list: List[float]) -> float:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Calculate Cluster Core Behavior Index (CBI)
        
        Formula: Cluster_CBI = Σ(ABW_i) / N
        
        STATUS: Replaced by calculate_cluster_strength() which uses logarithmic scaling.
        
        Args:
            abw_list: List of Adjusted Behavior Weights in the cluster
            
        Returns:
            float: Cluster CBI (average of ABWs)
        """
        if not abw_list:
            return 0.0
        
        cluster_cbi = sum(abw_list) / len(abw_list)
        
        logger.debug(
            f"Cluster CBI = sum({abw_list}) / {len(abw_list)} = {cluster_cbi:.6f}"
        )
        
        return cluster_cbi
    
    def select_canonical_behavior(
        self,
        behaviors_with_abw: List[Dict[str, Any]]
    ) -> str:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Select canonical behavior from cluster (highest ABW)
        
        STATUS: Replaced by select_canonical_label() which uses a different selection strategy.
        
        Args:
            behaviors_with_abw: List of dicts with 'behavior_id' and 'abw' keys
            
        Returns:
            str: behavior_id of canonical behavior
        """
        if not behaviors_with_abw:
            raise ValueError("Cannot select canonical from empty cluster")
        
        canonical = max(behaviors_with_abw, key=lambda x: x['abw'])
        
        logger.debug(
            f"Selected canonical behavior: {canonical['behavior_id']} "
            f"with ABW={canonical['abw']:.6f}"
        )
        
        return canonical['behavior_id']
    
    def assign_tier(self, cluster_cbi: float) -> TierEnum:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Assign tier based on Cluster CBI
        
        Rules:
        - PRIMARY: CBI ≥ 1.0
        - SECONDARY: 0.7 ≤ CBI < 1.0
        - NOISE: CBI < 0.7
        
        STATUS: Replaced by _assign_tier_by_strength() in cluster_analysis_pipeline.py
        which uses different thresholds for cluster strength.
        
        Args:
            cluster_cbi: Cluster Core Behavior Index
            
        Returns:
            TierEnum: PRIMARY, SECONDARY, or NOISE
        """
        if cluster_cbi >= self.primary_threshold:
            tier = TierEnum.PRIMARY
        elif cluster_cbi >= self.secondary_threshold:
            tier = TierEnum.SECONDARY
        else:
            tier = TierEnum.NOISE
        
        logger.debug(f"Cluster CBI {cluster_cbi:.6f} assigned to tier: {tier.value}")
        
        return tier
    
    def calculate_temporal_metrics(
        self,
        prompt_timestamps: List[int]
    ) -> TemporalSpan:
        """
        ⚠️ DEPRECATED - NOT USED IN CLUSTER-CENTRIC PIPELINE ⚠️
        
        Calculate temporal metrics for a behavior cluster
        
        STATUS: Temporal calculations are now done directly in cluster_analysis_pipeline.py
        
        Args:
            prompt_timestamps: List of Unix timestamps from related prompts
            
        Returns:
            TemporalSpan: Contains first_seen, last_seen, days_active
        """
        if not prompt_timestamps:
            raise ValueError("Cannot calculate temporal metrics from empty list")
        
        first_seen = min(prompt_timestamps)
        last_seen = max(prompt_timestamps)
        days_active = (last_seen - first_seen) / 86400
        
        logger.debug(
            f"Temporal metrics: first={first_seen}, last={last_seen}, "
            f"days_active={days_active:.2f}"
        )
        
        return TemporalSpan(
            first_seen=first_seen,
            last_seen=last_seen,
            days_active=days_active
        )
    
    def calculate_all_metrics_batch(
        self,
        behaviors: List[BehaviorObservation],
        current_timestamp: Optional[int] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate BW and ABW for multiple behaviors
        
        Args:
            behaviors: List of BehaviorObservation instances
            current_timestamp: Current Unix timestamp (defaults to now)
            
        Returns:
            dict: Maps observation_id to metrics dict
        """
        metrics = {}
        
        for behavior in behaviors:
            behavior_metrics = self.calculate_behavior_metrics(
                behavior, 
                current_timestamp
            )
            metrics[behavior.observation_id] = behavior_metrics
        
        logger.info(f"Calculated metrics for {len(behaviors)} behaviors")
        
        return metrics
    
    # ===== NEW CLUSTER-CENTRIC METHODS =====
    
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
        
        # Calculate days since each observation
        days_since = [(current_timestamp - ts) / 86400 for ts in timestamps]
        
        # Apply exponential decay (stronger for older observations)
        decay_rate = 0.01  # Same as default decay_rate
        weights = [math.exp(-decay_rate * days) for days in days_since]
        
        # Return average weight (how "recent" the cluster is overall)
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
        
        # --- NEW MULTIPLICATIVE MODEL (No Magic Numbers) ---
        # Requires BOTH consistency AND reinforcement to be high
        confidence = consistency_score * reinforcement_score
        
        # Optional: Small bonus for positive clarity trend (max 10% boost)
        if clarity_trend > 0:
            confidence = confidence * (1.0 + (clarity_trend * 0.1))
        
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
