"""
2D Projection Service for Embedding Visualization
Provides UMAP-based dimensionality reduction for behavior embedding visualization
"""
import logging
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    from umap import UMAP
    UMAP_AVAILABLE = True
except ImportError:
    logger.warning("UMAP not installed. 2D projections will use fallback method.")
    UMAP_AVAILABLE = False


def project_embeddings_to_2d(
    embeddings: List[List[float]],
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    random_state: int = 42
) -> List[Dict[str, float]]:
    """
    Project high-dimensional embeddings to 2D space for visualization
    
    Args:
        embeddings: List of embedding vectors
        n_neighbors: UMAP n_neighbors parameter (controls local vs global structure)
        min_dist: UMAP min_dist parameter (controls point spacing)
        random_state: Random seed for reproducibility
        
    Returns:
        List of 2D coordinates as [{"x": float, "y": float}, ...]
    """
    if not embeddings or len(embeddings) == 0:
        logger.warning("Empty embeddings provided")
        return []
    
    # Handle small datasets
    if len(embeddings) < 3:
        logger.warning(f"Only {len(embeddings)} embeddings - using fallback layout")
        return _fallback_2d_layout(len(embeddings))
    
    # Convert to numpy array
    embeddings_array = np.array(embeddings)
    
    # Check for valid embeddings
    if embeddings_array.shape[1] < 2:
        logger.error(f"Embeddings dimension too small: {embeddings_array.shape[1]}")
        return _fallback_2d_layout(len(embeddings))
    
    if UMAP_AVAILABLE:
        return _umap_projection(embeddings_array, n_neighbors, min_dist, random_state)
    else:
        logger.info("Using PCA fallback for 2D projection")
        return _pca_fallback(embeddings_array)


def _umap_projection(
    embeddings: np.ndarray,
    n_neighbors: int,
    min_dist: float,
    random_state: int
) -> List[Dict[str, float]]:
    """UMAP-based projection"""
    try:
        # Adjust n_neighbors if dataset is too small
        actual_n_neighbors = min(n_neighbors, len(embeddings) - 1)
        
        logger.info(f"Running UMAP on {len(embeddings)} embeddings (dim={embeddings.shape[1]})")
        
        reducer = UMAP(
            n_components=2,
            n_neighbors=actual_n_neighbors,
            min_dist=min_dist,
            random_state=random_state,
            metric='cosine'  # Use cosine similarity for semantic embeddings
        )
        
        projections = reducer.fit_transform(embeddings)
        
        # Convert to list of dicts
        result = [
            {"x": float(p[0]), "y": float(p[1])}
            for p in projections
        ]
        
        logger.info(f"UMAP projection complete: {len(result)} points")
        return result
        
    except Exception as e:
        logger.error(f"UMAP projection failed: {e}, using PCA fallback")
        return _pca_fallback(embeddings)


def _pca_fallback(embeddings: np.ndarray) -> List[Dict[str, float]]:
    """PCA-based fallback when UMAP is unavailable or fails"""
    try:
        from sklearn.decomposition import PCA
        
        logger.info(f"Running PCA fallback on {len(embeddings)} embeddings")
        
        pca = PCA(n_components=2, random_state=42)
        projections = pca.fit_transform(embeddings)
        
        result = [
            {"x": float(p[0]), "y": float(p[1])}
            for p in projections
        ]
        
        logger.info(f"PCA projection complete: {len(result)} points")
        return result
        
    except Exception as e:
        logger.error(f"PCA fallback failed: {e}, using random layout")
        return _fallback_2d_layout(len(embeddings))


def _fallback_2d_layout(count: int) -> List[Dict[str, float]]:
    """
    Simple grid layout fallback for when all else fails
    Arranges points in a circular pattern
    """
    logger.info(f"Using circular fallback layout for {count} points")
    
    result = []
    for i in range(count):
        angle = 2 * np.pi * i / max(count, 1)
        radius = 5.0
        result.append({
            "x": float(radius * np.cos(angle)),
            "y": float(radius * np.sin(angle))
        })
    
    return result


def normalize_2d_coordinates(
    coordinates: List[Dict[str, float]],
    target_range: tuple = (-10.0, 10.0)
) -> List[Dict[str, float]]:
    """
    Normalize 2D coordinates to a target range
    Useful for consistent visualization scaling
    
    Args:
        coordinates: List of {"x": float, "y": float}
        target_range: (min, max) tuple for normalization range
        
    Returns:
        Normalized coordinates
    """
    if not coordinates:
        return []
    
    # Extract x and y values
    x_vals = [c["x"] for c in coordinates]
    y_vals = [c["y"] for c in coordinates]
    
    # Find current ranges
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    
    # Avoid division by zero
    x_range = x_max - x_min if x_max != x_min else 1.0
    y_range = y_max - y_min if y_max != y_min else 1.0
    
    target_min, target_max = target_range
    target_span = target_max - target_min
    
    # Normalize
    normalized = []
    for c in coordinates:
        normalized.append({
            "x": target_min + ((c["x"] - x_min) / x_range) * target_span,
            "y": target_min + ((c["y"] - y_min) / y_range) * target_span
        })
    
    return normalized


def get_projection_metadata(coordinates: List[Dict[str, float]]) -> Dict:
    """
    Calculate metadata about the projection for debugging/monitoring
    """
    if not coordinates:
        return {"point_count": 0}
    
    x_vals = [c["x"] for c in coordinates]
    y_vals = [c["y"] for c in coordinates]
    
    return {
        "point_count": len(coordinates),
        "x_range": [min(x_vals), max(x_vals)],
        "y_range": [min(y_vals), max(y_vals)],
        "x_mean": np.mean(x_vals),
        "y_mean": np.mean(y_vals),
        "umap_available": UMAP_AVAILABLE
    }
