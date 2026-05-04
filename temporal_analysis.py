import numpy as np
import pymannkendall as mk
from typing import List
from datetime import datetime

from logger import get_logger

log = get_logger(__name__)

class TemporalAnalyzer:
    """
    Implements Stage 2 of the CBIE Methodology: Temporal Analysis.
    Measures habit consistency using Gini Coefficient of inter-event times, 
    and habit trends using the Mann-Kendall Trend Test.
    """

    def calculate_inter_event_times(self, timestamps: List[str]) -> np.ndarray:
        """
        Converts datetime strings to sorted inter-event times (in days).
        """
        if len(timestamps) < 2:
            return np.array([])
            
        # Parse timestamps (assumes ISO 8601 string format)
        times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in timestamps]
        times.sort()
        
        # Calculate differences in days
        diffs = [(times[i] - times[i-1]).total_seconds() / (24 * 3600) for i in range(1, len(times))]
        return np.array(diffs)

    def calculate_consistency(self, timestamps: List[str], reinforcement_counts: List[int] = None) -> float:
        """
        Computes the Consistency Score using the Gini Coefficient of inter-event times.
        A lower Gini implies higher consistency (intervals are similar).
        Returns a score between 0.0 (perfectly consistent) and 1.0 (highly inconsistent).
        If not enough data, returns 1.0 by default.

        reinforcement_counts: Optional list of counts per behaviour row.  When the
                              BAC aggregates repeated observations into a single row
                              (incrementing reinforcement_count instead of creating
                              new rows), we lose the individual timestamps needed
                              for the Gini calculation.  This parameter enables a
                              heuristic fallback that partially compensates.
        """
        diffs = self.calculate_inter_event_times(timestamps)
        
        if len(diffs) < 1:
             # ──────────────────────────────────────────────────────────────
             # HEURISTIC CONSISTENCY ADJUSTMENT FOR AGGREGATED ROWS
             # ──────────────────────────────────────────────────────────────
             # Problem: The BAC database aggregates repeated identical
             #   behaviours into a single row and increments
             #   reinforcement_count rather than inserting new rows.
             #   With only 1 timestamp we cannot compute inter-event
             #   intervals, so the Gini coefficient is undefined.
             #
             # Solution: Apply a linear penalty reduction based on the
             #   total reinforcement count across the cluster.
             #
             # Justification of chosen constants:
             #
             #   DECAY_STEP = 0.1
             #     The Confirmation Model assigns consistency a weight of
             #     0.35 (the highest AHP weight).  On the normalised
             #     [0, 1] scale, moving from 1.0 → 0.5 spans 0.5 units
             #     over 5 reinforcements (counts 2–6), giving a step of
             #     0.5 / 5 = 0.1.  This produces a perceptible but
             #     conservative improvement in the final core score
             #     (~0.035 per reinforcement), avoiding the over-
             #     confirmation seen with virtual row expansion.
             #
             #   FLOOR = 0.5  (Gini midpoint)
             #     A Gini of 0.5 is the theoretical boundary between
             #     "moderately consistent" and "inconsistent" distributions.
             #     Since we have no actual temporal spread data, capping at
             #     0.5 means we never grant better-than-average consistency
             #     purely from repetition count — real multi-timestamp
             #     evidence is still needed to reach scores below 0.5.
             #
             #   FLOOR reached at count ≥ 6
             #     In small-sample statistics, n ≥ 5–6 observations is the
             #     commonly accepted minimum for basic descriptive measures
             #     (e.g., the Mann-Kendall test in this engine requires
             #     n ≥ 4).  Treating 6 repetitions as the saturation point
             #     aligns with this convention — beyond 6, additional
             #     repetitions without new timestamps provide diminishing
             #     evidence of temporal regularity.
             # ──────────────────────────────────────────────────────────────
             DECAY_STEP = 0.1
             FLOOR = 0.5

             total_reinforcement = sum(reinforcement_counts) if reinforcement_counts else 1
             if total_reinforcement > 1:
                 heuristic_score = max(FLOOR, 1.0 - (DECAY_STEP * (total_reinforcement - 1)))
                 log.info(
                     "Heuristic consistency applied (insufficient timestamps)",
                     extra={
                         "stage": "TEMPORAL_ANALYSIS",
                         "total_reinforcement": total_reinforcement,
                         "heuristic_consistency": round(heuristic_score, 3),
                     },
                 )
                 return float(heuristic_score)
             
             return 1.0  # Single occurrence, no reinforcement — no evidence of consistency
             
        # Gini computation
        array = np.sort(diffs)
        index = np.arange(1, array.shape[0] + 1)
        n = array.shape[0]
        # Calculate mean safely to avoid division by zero
        mean_diff = np.mean(array)
        if mean_diff == 0:
             return 0.0 # Perfectly consistent if all intervals are exactly 0

        gini = ((np.sum((2 * index - n  - 1) * array)) / (n * np.sum(array)))
        return float(gini)

    def calculate_trend(self, scores: List[float]) -> float:
        """
        Applies the Mann-Kendall Trend Test to a sequence of scores to check
        for statistical momentum (e.g. increasing engagement).
        
        Returns:
            1.0 indicating a strong upward trend.
           -1.0 indicating a strong downward trend.
            0.0 indicating no significant trend.
        """
        if len(scores) < 4:
            # Mann-Kendall requires at least 4 data points for meaningful results
            return 0.0
            
        try:
            # Alpha=0.10 allows for better trend detection on sparse/small behavioral datasets
            result = mk.original_test(scores, alpha=0.10)
            
            # Map trend string to numerical score
            if result.trend == 'increasing':
                return 1.0
            elif result.trend == 'decreasing':
                return -1.0
            else:
                return 0.0
                
        except Exception as e:
            log.error("Error calculating Mann-Kendall trend", extra={"stage": "TEMPORAL_ANALYSIS", "error": str(e)})
            return 0.0
