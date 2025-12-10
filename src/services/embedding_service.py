"""
Embedding Service for CBIE System
Interfaces with Azure OpenAI for generating behavior embeddings
"""
from typing import List, Optional
import logging
from openai import AzureOpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Azure OpenAI"""
    
    def __init__(self):
        self.client: Optional[AzureOpenAI] = None
        self.model = settings.openai_embedding_model
        
    def connect(self):
        """Initialize Azure OpenAI client"""
        try:
            self.client = AzureOpenAI(
                api_key=settings.openai_api_key,
                api_version=settings.openai_api_version,
                azure_endpoint=settings.openai_api_base
            )
            logger.info(f"Connected to Azure OpenAI for embeddings: {self.model}")
        except Exception as e:
            logger.error(f"Failed to connect to Azure OpenAI: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List[float]: Embedding vector (3072 dimensions for text-embedding-3-large)
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text: {text[:50]}...")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            if not texts:
                return []
            
            # Azure OpenAI supports batch embedding
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    
    def generate_embeddings_for_behaviors(
        self,
        behavior_texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for behavior texts with batching
        
        Args:
            behavior_texts: List of behavior text strings
            batch_size: Number of texts to process per batch
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(behavior_texts), batch_size):
            batch = behavior_texts[i:i + batch_size]
            batch_embeddings = self.generate_embeddings_batch(batch)
            all_embeddings.extend(batch_embeddings)
            
            logger.info(
                f"Processed batch {i // batch_size + 1}: "
                f"{len(batch_embeddings)} embeddings"
            )
        
        return all_embeddings


# Global embedding service instance
embedding_service = EmbeddingService()
