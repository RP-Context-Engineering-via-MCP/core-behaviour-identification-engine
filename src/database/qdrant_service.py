"""Qdrant vector database service for CBIE system"""
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from qdrant_client.http.exceptions import UnexpectedResponse
import logging
import uuid

from src.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for Qdrant vector database operations"""
    
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collection_name = settings.qdrant_collection
        self.vector_size = 3072  # text-embedding-3-large dimension
        
    def connect(self):
        """Establish Qdrant connection and ensure collection exists"""
        try:
            self.client = QdrantClient(url=settings.qdrant_url)
            
            # Create collection if it doesn't exist
            self._ensure_collection()
            
            logger.info(f"Connected to Qdrant: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def disconnect(self):
        """Close Qdrant connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from Qdrant")
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def insert_embeddings(
        self, 
        embeddings: List[List[float]], 
        behavior_ids: List[str],
        behavior_texts: List[str],
        user_id: str,
        timestamps: List[int]
    ) -> bool:
        """
        Insert behavior embeddings into Qdrant
        
        Args:
            embeddings: List of embedding vectors
            behavior_ids: List of behavior IDs
            behavior_texts: List of behavior text strings
            user_id: User ID
            timestamps: List of timestamps
            
        Returns:
            bool: Success status
        """
        try:
            if len(embeddings) != len(behavior_ids) != len(behavior_texts) != len(timestamps):
                raise ValueError("All input lists must have the same length")
            
            points = []
            for i, (embedding, behavior_id, text, timestamp) in enumerate(
                zip(embeddings, behavior_ids, behavior_texts, timestamps)
            ):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "behavior_id": behavior_id,
                        "behavior_text": text,
                        "user_id": user_id,
                        "timestamp": timestamp
                    }
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Inserted {len(points)} embeddings for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting embeddings: {e}")
            return False
    
    def insert_behaviors_with_embeddings(
        self, 
        embeddings: List[List[float]], 
        behaviors: List[Dict[str, Any]]
    ) -> bool:
        """
        Insert complete behavior data with embeddings into Qdrant
        
        Args:
            embeddings: List of embedding vectors
            behaviors: List of complete behavior dictionaries with all metadata
            
        Returns:
            bool: Success status
        """
        try:
            if len(embeddings) != len(behaviors):
                raise ValueError("Embeddings and behaviors lists must have the same length")
            
            points = []
            for i, (embedding, behavior) in enumerate(zip(embeddings, behaviors)):
                # Create payload with all behavior metadata
                payload = {
                    "behavior_id": behavior.get("behavior_id"),
                    "behavior_text": behavior.get("behavior_text"),
                    "user_id": behavior.get("user_id"),
                    "session_id": behavior.get("session_id"),
                    "credibility": behavior.get("credibility"),
                    "reinforcement_count": behavior.get("reinforcement_count"),
                    "decay_rate": behavior.get("decay_rate"),
                    "created_at": behavior.get("created_at"),
                    "last_seen": behavior.get("last_seen"),
                    "timestamp": behavior.get("timestamp"),  # Add timestamp field
                    "clarity_score": behavior.get("clarity_score"),
                    "extraction_confidence": behavior.get("extraction_confidence"),
                    "prompt_history_ids": behavior.get("prompt_history_ids", [])
                }
                
                # Add optional fields if they exist
                if "domain" in behavior:
                    payload["domain"] = behavior["domain"]
                if "expertise_level" in behavior:
                    payload["expertise_level"] = behavior["expertise_level"]
                
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Inserted {len(points)} complete behaviors with embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting complete behaviors: {e}")
            return False
    
    def insert_behavior(
        self,
        user_id: str,
        behavior_id: str,
        behavior_text: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Insert a single behavior with embedding into Qdrant
        
        Args:
            user_id: User ID
            behavior_id: Behavior/observation ID
            behavior_text: Behavior text
            embedding: Embedding vector
            metadata: Additional metadata (credibility, clarity, timestamp, etc.)
            
        Returns:
            bool: Success status
        """
        try:
            payload = {
                "behavior_id": behavior_id,
                "observation_id": behavior_id,  # Add observation_id for cluster-centric approach
                "behavior_text": behavior_text,
                "user_id": user_id
            }
            
            # Add metadata if provided
            if metadata:
                payload.update(metadata)
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Inserted behavior {behavior_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting behavior: {e}")
            return False
    
    def get_embeddings_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all embeddings for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            List of dictionaries containing id, vector, and payload
        """
        try:
            # Scroll through all points with user_id filter
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=1000,  # Adjust as needed
                with_payload=True,
                with_vectors=True
            )
            
            results = []
            for point in points:
                results.append({
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                })
            
            logger.info(f"Retrieved {len(results)} embeddings for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving embeddings: {e}")
            return []
    
    def get_embedding_by_behavior_id(self, behavior_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve embedding for a specific behavior
        
        Args:
            behavior_id: Behavior ID
            
        Returns:
            Dictionary containing id, vector, and payload, or None
        """
        try:
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="behavior_id",
                            match=MatchValue(value=behavior_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=True
            )
            
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                }
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving embedding for behavior {behavior_id}: {e}")
            return None
    
    def search_similar_behaviors(
        self, 
        query_vector: List[float], 
        user_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar behaviors using vector similarity
        
        Args:
            query_vector: Query embedding vector
            user_id: User ID to filter by
            top_k: Number of results to return
            
        Returns:
            List of similar behaviors with scores
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=top_k,
                with_payload=True
            )
            
            similar = []
            for result in results:
                similar.append({
                    "behavior_id": result.payload["behavior_id"],
                    "behavior_text": result.payload["behavior_text"],
                    "score": result.score,
                    "payload": result.payload
                })
            
            return similar
            
        except Exception as e:
            logger.error(f"Error searching similar behaviors: {e}")
            return []
    
    def delete_embeddings_by_user(self, user_id: str) -> bool:
        """
        Delete all embeddings for a specific user
        
        Args:
            user_id: User ID
            
        Returns:
            bool: Success status
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )
            )
            
            logger.info(f"Deleted embeddings for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embeddings: {e}")
            return False
    
    def delete_embedding_by_behavior_id(self, behavior_id: str) -> bool:
        """
        Delete embedding for a specific behavior
        
        Args:
            behavior_id: Behavior ID
            
        Returns:
            bool: Success status
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="behavior_id",
                            match=MatchValue(value=behavior_id)
                        )
                    ]
                )
            )
            
            logger.info(f"Deleted embedding for behavior {behavior_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")
            return False


# Global Qdrant service instance
qdrant_service = QdrantService()
