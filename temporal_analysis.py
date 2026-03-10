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

    def calculate_consistency(self, timestamps: List[str]) -> float:
        """
        Computes the Consistency Score using the Gini Coefficient of inter-event times.
        A lower Gini implies higher consistency (intervals are similar).
        Returns a score between 0.0 (perfectly consistent) and 1.0 (highly inconsistent).
        If not enough data, returns 1.0 by default.
        """
        diffs = self.calculate_inter_event_times(timestamps)
        
        if len(diffs) < 1:
             return 1.0 # Cannot determine consistency with < 2 events
             
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
