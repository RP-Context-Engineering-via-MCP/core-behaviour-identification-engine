import math
from typing import Optional, List, Dict, Any
import logging
import time
import warnings

logger = logging.getLogger(__name__)


class CalculationEngine:
    """Engine for calculating behavior weights and metrics"""
    
    def __init__(self, alpha: float = 0.35, beta: float = 0.40, gamma: float = 0.25):
        """
        Initialize calculation engine with formula parameters
        
        Args:
            alpha: Weight for credibility (default: 0.35)
            beta: Weight for clarity (default: 0.40)
            gamma: Weight for extraction confidence (default: 0.25)
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.reinforcement_multiplier = 0.01
    
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
        
        Args:
            credibility: Trustworthiness (0-1)
            clarity_score: Explicitness (0-1)
            extraction_confidence: Model confidence (0-1)
            
        Returns:
            float: Behavior Weight
        """
        warnings.warn(
            "calculate_behavior_weight is DEPRECATED. "
            "Use cluster-centric methods instead.",
            DeprecationWarning
        )
        
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
        
        Args:
            behavior_weight: Base behavior weight
            reinforcement_count: Number of times behavior repeated
            decay_rate: Temporal decay rate
            days_since_last_seen: Days since last observation
            
        Returns:
            float: Adjusted Behavior Weight
        """
        warnings.warn(
            "calculate_adjusted_behavior_weight is DEPRECATED. "
            "Use cluster-centric methods instead.",
            DeprecationWarning
        )
        
        reinforcement_factor = 1 + (reinforcement_count * self.reinforcement_multiplier)
        temporal_decay = math.exp(-decay_rate * days_since_last_seen)
        
        abw = behavior_weight * reinforcement_factor * temporal_decay
        
        logger.debug(
            f"ABW = {behavior_weight:.6f} × {reinforcement_factor:.6f} × {temporal_decay:.6f} = {abw:.6f}"
        )
        
        return abw
    
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
        recency_factor = self.calculate_recency_factor(timestamps, current_timestamp)
        
        # Raw strength (unbounded)
        raw_strength = size_factor * mean_abw * recency_factor
        
        # Normalize using sigmoid-like function: x / (1 + x)
        normalized_strength = raw_strength / (1 + raw_strength)
        
        logger.debug(
            f"Cluster strength: log({cluster_size}+1)={size_factor:.2f} * ABW={mean_abw:.2f} * "
            f"Recency={recency_factor:.2f} = Raw={raw_strength:.2f} → Normalized={normalized_strength:.4f}"
        )
        
        return round(normalized_strength, 4)
    
    def calculate_cluster_confidence(
        self,
        observations: List[Any],
        cluster_size: int
    ) -> float:
        """
        Calculate cluster confidence score
        
        Args:
            observations: List of BehaviorObservation objects
            cluster_size: Size of the cluster
            
        Returns:
            float: Confidence score (0-1)
        """
        if not observations:
            return 0.0
        
        # Calculate consistency (how similar the observations are)
        clarity_scores = [obs.clarity_score for obs in observations]
        consistency_score = sum(clarity_scores) / len(clarity_scores)
        
        # Reinforcement score based on cluster size
        reinforcement_score = min(1.0, math.log(cluster_size + 1) / 3.0)
        
        # Multiplicative confidence
        confidence = consistency_score * reinforcement_score
        
        logger.debug(
            f"Cluster confidence: consistency={consistency_score:.4f} * "
            f"reinforcement={reinforcement_score:.4f} = {confidence:.4f}"
        )
        
        return round(confidence, 4)
    
    def select_canonical_label(
        self,
        observations: List[Any]
    ) -> str:
        """
        Select canonical label for cluster
        
        Args:
            observations: List of BehaviorObservation objects
            
        Returns:
            str: Canonical label (longest/most descriptive text)
        """
        if not observations:
            return "Unknown behavior"
        
        # Select longest behavior text as canonical label
        canonical = max(observations, key=lambda obs: len(obs.behavior_text))
        
        logger.debug(f"Selected canonical label: {canonical.behavior_text[:50]}...")
        
        return canonical.behavior_text
    
    def calculate_recency_factor(
        self,
        timestamps: List[int],
        current_timestamp: int,
        decay_rate: float = 0.01
    ) -> float:
        """
        Calculate temporal recency factor for cluster
        
        Args:
            timestamps: List of observation timestamps
            current_timestamp: Current time
            decay_rate: Decay rate for temporal weighting
            
        Returns:
            float: Recency factor
        """
        if not timestamps:
            return 0.0
        
        # Calculate weighted average of recency
        total_weight = 0.0
        for ts in timestamps:
            days_ago = (current_timestamp - ts) / 86400
            weight = math.exp(-decay_rate * days_ago)
            total_weight += weight
        
        recency_factor = total_weight / len(timestamps)
        
        logger.debug(f"Recency factor: {recency_factor:.4f}")
        
        return recency_factor
