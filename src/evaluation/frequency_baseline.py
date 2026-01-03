"""
Frequency-based baseline for preference classification.

This is a deliberately simple baseline that classifies behaviors
based solely on reinforcement count, without clustering or stability checks.
It represents the naive approach of "count occurrences = preference strength".
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class FrequencyStatus(str, Enum):
    """Classification status based on frequency thresholds."""
    CORE = "CORE"
    SECONDARY = "SECONDARY"
    NOISE = "NOISE"


@dataclass
class FrequencyClassification:
    """Result of frequency-based classification."""
    behavior_id: str
    behavior_description: str
    total_reinforcements: int
    status: FrequencyStatus
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "behavior_id": self.behavior_id,
            "behavior_description": self.behavior_description,
            "total_reinforcements": self.total_reinforcements,
            "status": self.status.value,
            "confidence": self.confidence
        }


class FrequencyBaseline:
    """
    Naive frequency-based preference classifier.
    
    This baseline intentionally:
    - Does NOT use clustering
    - Does NOT check semantic coherence
    - Does NOT use stability measures
    - Only counts reinforcement occurrences
    
    It represents what a simple recommendation system might do:
    "If user did X many times, they must prefer X"
    """
    
    def __init__(
        self,
        core_threshold: int = 5,
        secondary_threshold: int = 2,
        max_reinforcements_for_scaling: int = 50
    ):
        """
        Initialize frequency baseline classifier.
        
        Args:
            core_threshold: Minimum reinforcements for CORE status (default: 5)
            secondary_threshold: Minimum reinforcements for SECONDARY status (default: 2)
            max_reinforcements_for_scaling: Cap for confidence scaling (default: 50)
        """
        self.core_threshold = core_threshold
        self.secondary_threshold = secondary_threshold
        self.max_reinforcements = max_reinforcements_for_scaling
    
    def classify_behaviors(
        self,
        behaviors: List[Dict[str, Any]]
    ) -> List[FrequencyClassification]:
        """
        Classify behaviors based on reinforcement frequency.
        
        Args:
            behaviors: List of behavior dicts with structure:
                {
                    "behavior_id": str,
                    "description": str,
                    "prompts": [
                        {"reinforcement_count": int, ...},
                        ...
                    ]
                }
        
        Returns:
            List of FrequencyClassification objects
        """
        classifications = []
        
        for behavior in behaviors:
            # Count total reinforcements across all prompts
            total_reinforcements = sum(
                prompt.get("reinforcement_count", 0)
                for prompt in behavior.get("prompts", [])
            )
            
            # Simple threshold-based classification
            if total_reinforcements >= self.core_threshold:
                status = FrequencyStatus.CORE
                # Scale confidence from 0 to 1 based on reinforcement count
                confidence = min(1.0, total_reinforcements / self.max_reinforcements)
            elif total_reinforcements >= self.secondary_threshold:
                status = FrequencyStatus.SECONDARY
                # Lower confidence for secondary
                confidence = total_reinforcements / (self.core_threshold * 2)
            else:
                status = FrequencyStatus.NOISE
                confidence = 0.1
            
            classification = FrequencyClassification(
                behavior_id=behavior.get("behavior_id", ""),
                behavior_description=behavior.get("description", ""),
                total_reinforcements=total_reinforcements,
                status=status,
                confidence=confidence
            )
            
            classifications.append(classification)
        
        return classifications
    
    def get_core_behaviors(
        self,
        behaviors: List[Dict[str, Any]]
    ) -> List[FrequencyClassification]:
        """
        Get only behaviors classified as CORE.
        
        Args:
            behaviors: List of behavior dicts
        
        Returns:
            List of CORE-classified behaviors
        """
        all_classifications = self.classify_behaviors(behaviors)
        return [c for c in all_classifications if c.status == FrequencyStatus.CORE]
    
    def get_summary_stats(
        self,
        classifications: List[FrequencyClassification]
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics for classifications.
        
        Args:
            classifications: List of FrequencyClassification objects
        
        Returns:
            Dictionary with summary statistics
        """
        total = len(classifications)
        core_count = sum(1 for c in classifications if c.status == FrequencyStatus.CORE)
        secondary_count = sum(1 for c in classifications if c.status == FrequencyStatus.SECONDARY)
        noise_count = sum(1 for c in classifications if c.status == FrequencyStatus.NOISE)
        
        total_reinforcements = sum(c.total_reinforcements for c in classifications)
        avg_reinforcements = total_reinforcements / total if total > 0 else 0
        
        core_reinforcements = [
            c.total_reinforcements 
            for c in classifications 
            if c.status == FrequencyStatus.CORE
        ]
        
        return {
            "total_behaviors": total,
            "core_count": core_count,
            "secondary_count": secondary_count,
            "noise_count": noise_count,
            "core_percentage": (core_count / total * 100) if total > 0 else 0,
            "total_reinforcements": total_reinforcements,
            "avg_reinforcements": avg_reinforcements,
            "core_reinforcements_range": {
                "min": min(core_reinforcements) if core_reinforcements else 0,
                "max": max(core_reinforcements) if core_reinforcements else 0,
                "avg": sum(core_reinforcements) / len(core_reinforcements) if core_reinforcements else 0
            }
        }


def main():
    """Example usage of frequency baseline."""
    # Example behaviors
    example_behaviors = [
        {
            "behavior_id": "b1",
            "description": "prefers step-by-step guides",
            "prompts": [
                {"reinforcement_count": 42},
            ]
        },
        {
            "behavior_id": "b2",
            "description": "learns by examples",
            "prompts": [
                {"reinforcement_count": 41},
            ]
        },
        {
            "behavior_id": "b3",
            "description": "likes quick summaries",
            "prompts": [
                {"reinforcement_count": 4},
            ]
        },
        {
            "behavior_id": "b4",
            "description": "rare behavior",
            "prompts": [
                {"reinforcement_count": 1},
            ]
        }
    ]
    
    baseline = FrequencyBaseline()
    classifications = baseline.classify_behaviors(example_behaviors)
    
    print("Frequency Baseline Classifications:")
    print("=" * 80)
    for c in classifications:
        print(f"{c.behavior_description:40} | {c.total_reinforcements:3} reinforcements | {c.status.value:9} | confidence: {c.confidence:.2f}")
    
    print("\nSummary Statistics:")
    print("=" * 80)
    stats = baseline.get_summary_stats(classifications)
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
