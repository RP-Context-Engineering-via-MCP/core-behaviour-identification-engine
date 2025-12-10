"""
Clustering Engine for CBIE System
Implements HDBSCAN clustering for semantic behavior grouping
"""
from typing import List, Dict, Any, Tuple
import numpy as np
from hdbscan import HDBSCAN
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """Engine for clustering behavior embeddings using HDBSCAN"""
    
    def __init__(self):
        # Clustering parameters from settings
        self.min_cluster_size = settings.min_cluster_size  # 2
        self.min_samples = settings.min_samples  # 1
        self.cluster_selection_epsilon = settings.cluster_selection_epsilon  # 0.15
        # Use 'euclidean' metric on normalized vectors (equivalent to cosine for clustering)
        self.metric = 'euclidean'
        
    def cluster_behaviors(
        self,
        embeddings: List[List[float]],
        behavior_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Cluster behavior embeddings using HDBSCAN
        CRITICAL: ALL cluster members are preserved - NOTHING is discarded
        
        Args:
            embeddings: List of embedding vectors
            behavior_ids: List of corresponding observation IDs
            
        Returns:
            dict: Clustering results containing:
                - clusters: Dict mapping cluster_id to ALL observation_ids (NEVER DISCARD)
                - cluster_sizes: Dict mapping cluster_id to member count
                - cluster_embeddings: Dict mapping cluster_id to list of member embeddings
                - cluster_centroids: Dict mapping cluster_id to centroid embedding
                - intra_cluster_distances: Dict mapping cluster_id to distance statistics
                - labels: List of cluster labels (same order as behavior_ids)
                - noise_behaviors: List of behavior_ids assigned to noise (-1)
                - num_clusters: Number of valid clusters (excluding noise)
                - normalized_embeddings: The normalized embedding array used
        """
        try:
            if len(embeddings) != len(behavior_ids):
                raise ValueError("Embeddings and behavior_ids must have same length")
            
            if len(embeddings) < self.min_cluster_size:
                logger.warning(
                    f"Not enough behaviors ({len(embeddings)}) for clustering. "
                    f"Minimum required: {self.min_cluster_size}"
                )
                return {
                    "clusters": {},
                    "cluster_sizes": {},
                    "cluster_embeddings": {},
                    "cluster_centroids": {},
                    "intra_cluster_distances": {},
                    "labels": [-1] * len(behavior_ids),
                    "noise_behaviors": behavior_ids,
                    "num_clusters": 0,
                    "normalized_embeddings": np.array([])
                }
            
            # Convert to numpy array
            X = np.array(embeddings)
            
            # Normalize embeddings for euclidean distance clustering
            # (equivalent to cosine similarity clustering)
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            X_normalized = X / (norms + 1e-10)  # Add small epsilon to avoid division by zero
            
            # Initialize HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                cluster_selection_epsilon=self.cluster_selection_epsilon,
                metric=self.metric,
                cluster_selection_method='eom'
            )
            
            # Perform clustering on normalized embeddings
            cluster_labels = clusterer.fit_predict(X_normalized)
            
            # Organize results - PRESERVE EVERYTHING
            clusters = {}
            cluster_embeddings = {}
            cluster_centroids = {}
            cluster_sizes = {}
            intra_cluster_distances = {}
            noise_behaviors = []
            
            # Build cluster membership (NO DISCARDING)
            for behavior_id, label, embedding in zip(behavior_ids, cluster_labels, X_normalized):
                if label == -1:
                    noise_behaviors.append(behavior_id)
                else:
                    cluster_id = f"cluster_{label}"
                    if cluster_id not in clusters:
                        clusters[cluster_id] = []
                        cluster_embeddings[cluster_id] = []
                    
                    clusters[cluster_id].append(behavior_id)
                    cluster_embeddings[cluster_id].append(embedding)
            
            # Calculate cluster statistics (centroid, distances, etc.)
            for cluster_id in clusters.keys():
                member_embeddings = np.array(cluster_embeddings[cluster_id])
                
                # Calculate centroid
                centroid = np.mean(member_embeddings, axis=0)
                cluster_centroids[cluster_id] = centroid.tolist()
                
                # Calculate cluster size
                cluster_sizes[cluster_id] = len(clusters[cluster_id])
                
                # Calculate intra-cluster distances
                distances = []
                for emb in member_embeddings:
                    dist = np.linalg.norm(emb - centroid)
                    distances.append(dist)
                
                intra_cluster_distances[cluster_id] = {
                    "mean": float(np.mean(distances)),
                    "std": float(np.std(distances)),
                    "min": float(np.min(distances)),
                    "max": float(np.max(distances)),
                    "all_distances": [float(d) for d in distances]
                }
            
            num_clusters = len(clusters)
            
            logger.info(
                f"Clustering complete: {num_clusters} clusters formed, "
                f"{len(noise_behaviors)} noise observations"
            )
            
            for cluster_id, members in clusters.items():
                logger.debug(
                    f"{cluster_id}: {len(members)} observations, "
                    f"mean distance: {intra_cluster_distances[cluster_id]['mean']:.4f}"
                )
            
            return {
                "clusters": clusters,  # ALL members preserved
                "cluster_sizes": cluster_sizes,
                "cluster_embeddings": cluster_embeddings,
                "cluster_centroids": cluster_centroids,
                "intra_cluster_distances": intra_cluster_distances,
                "labels": cluster_labels.tolist(),
                "noise_behaviors": noise_behaviors,
                "num_clusters": num_clusters,
                "normalized_embeddings": X_normalized,
                "clusterer": clusterer  # For debugging/analysis
            }
            
        except Exception as e:
            logger.error(f"Error during clustering: {e}")
            raise
    
    def get_cluster_statistics(
        self,
        clustering_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate statistics about clustering results
        
        Args:
            clustering_result: Result from cluster_behaviors()
            
        Returns:
            dict: Statistics about clusters
        """
        clusters = clustering_result["clusters"]
        noise_behaviors = clustering_result["noise_behaviors"]
        
        if not clusters:
            return {
                "num_clusters": 0,
                "total_behaviors": len(noise_behaviors),
                "noise_count": len(noise_behaviors),
                "avg_cluster_size": 0,
                "min_cluster_size": 0,
                "max_cluster_size": 0
            }
        
        cluster_sizes = [len(members) for members in clusters.values()]
        
        stats = {
            "num_clusters": len(clusters),
            "total_behaviors": sum(cluster_sizes) + len(noise_behaviors),
            "noise_count": len(noise_behaviors),
            "avg_cluster_size": np.mean(cluster_sizes),
            "min_cluster_size": min(cluster_sizes),
            "max_cluster_size": max(cluster_sizes),
            "cluster_size_distribution": cluster_sizes
        }
        
        logger.info(f"Cluster statistics: {stats}")
        
        return stats
    
    def map_behaviors_to_clusters(
        self,
        clustering_result: Dict[str, Any],
        behavior_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map behaviors with their metrics to cluster assignments
        
        Args:
            clustering_result: Result from cluster_behaviors()
            behavior_metrics: Dict mapping behavior_id to metrics (bw, abw, etc.)
            
        Returns:
            dict: Maps cluster_id to list of behaviors with metrics
        """
        clusters = clustering_result["clusters"]
        
        cluster_data = {}
        
        for cluster_id, behavior_ids in clusters.items():
            cluster_behaviors = []
            
            for behavior_id in behavior_ids:
                if behavior_id in behavior_metrics:
                    behavior_data = {
                        "behavior_id": behavior_id,
                        **behavior_metrics[behavior_id]
                    }
                    cluster_behaviors.append(behavior_data)
            
            cluster_data[cluster_id] = cluster_behaviors
        
        logger.debug(f"Mapped {len(clusters)} clusters with behavior metrics")
        
        return cluster_data
    
    def validate_clustering_quality(
        self,
        clustering_result: Dict[str, Any],
        min_valid_clusters: int = 1
    ) -> Tuple[bool, str]:
        """
        Validate clustering quality
        
        Args:
            clustering_result: Result from cluster_behaviors()
            min_valid_clusters: Minimum number of valid clusters required
            
        Returns:
            tuple: (is_valid, message)
        """
        num_clusters = clustering_result["num_clusters"]
        noise_count = len(clustering_result["noise_behaviors"])
        total = num_clusters + (1 if noise_count > 0 else 0)
        
        if num_clusters < min_valid_clusters:
            return False, f"Too few clusters formed: {num_clusters} < {min_valid_clusters}"
        
        if noise_count > 0:
            noise_ratio = noise_count / (noise_count + sum(
                len(members) for members in clustering_result["clusters"].values()
            ))
            if noise_ratio > 0.5:
                logger.warning(f"High noise ratio: {noise_ratio:.2%}")
        
        return True, f"Clustering valid: {num_clusters} clusters formed"


# Global clustering engine instance
clustering_engine = ClusteringEngine()
