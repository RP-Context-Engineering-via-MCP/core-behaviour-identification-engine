import numpy as np
from typing import List, Dict, Any
import logging
from hdbscan import HDBSCAN

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """Engine for clustering behavior embeddings using HDBSCAN"""
    
    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        cluster_selection_epsilon: float = 0.1,
        metric: str = "cosine"
    ):
        """
        Initialize clustering engine
        
        Args:
            min_cluster_size: Minimum size of clusters
            min_samples: Minimum samples in neighborhood
            cluster_selection_epsilon: Distance threshold for merging clusters
            metric: Distance metric to use
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.metric = metric
        
        logger.info(
            f"Initialized ClusteringEngine: min_cluster_size={min_cluster_size}, "
            f"min_samples={min_samples}, epsilon={cluster_selection_epsilon}"
        )
    
    def cluster_behaviors(
        self,
        embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """
        Cluster behavior embeddings using HDBSCAN
        
        Args:
            embeddings: Array of embedding vectors (N x D)
            
        Returns:
            Dict containing cluster labels and metadata
        """
        if len(embeddings) < self.min_cluster_size:
            logger.warning(
                f"Not enough embeddings ({len(embeddings)}) for clustering "
                f"(min required: {self.min_cluster_size})"
            )
            return {
                "labels": np.array([-1] * len(embeddings)),
                "n_clusters": 0,
                "n_noise": len(embeddings)
            }
        
        logger.info(f"Clustering {len(embeddings)} embeddings...")
        
        # Initialize HDBSCAN
        clusterer = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric=self.metric
        )
        
        # Fit and predict
        labels = clusterer.fit_predict(embeddings)
        
        # Calculate statistics
        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_noise = list(labels).count(-1)
        
        logger.info(
            f"Clustering complete: {n_clusters} clusters, {n_noise} noise points"
        )
        
        return {
            "labels": labels,
            "n_clusters": n_clusters,
            "n_noise": n_noise,
            "probabilities": clusterer.probabilities_ if hasattr(clusterer, 'probabilities_') else None
        }
