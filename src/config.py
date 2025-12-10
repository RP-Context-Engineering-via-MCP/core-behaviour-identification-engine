"""Configuration management for CBIE system"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    mongodb_url: str
    mongodb_database: str
    qdrant_url: str
    qdrant_collection: str
    
    # OpenAI Configuration
    openai_api_key: str
    openai_embedding_model: str
    openai_api_type: str
    openai_api_base: str
    openai_api_version: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Formula Parameters (from documentation)
    alpha: float = 0.35  # credibility weight
    beta: float = 0.40   # clarity weight
    gamma: float = 0.25  # extraction confidence weight
    reinforcement_multiplier: float = 0.01
    primary_threshold: float = 1.0
    secondary_threshold: float = 0.7
    
    # Clustering Parameters
    min_cluster_size: int = 2
    min_samples: int = 1
    cluster_selection_epsilon: float = 0.15
    
    class Config:
        # Use absolute path to .env file (project root)
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
