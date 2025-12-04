from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from src.config import settings
from src.database.mongodb_service import MongoDBService
from src.services.embedding_service import EmbeddingService
from src.services.archetype_service import ArchetypeService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
mongo_service = MongoDBService(
    connection_string=settings.mongodb_url,
    database_name=settings.mongodb_database
)

embedding_service = EmbeddingService()
archetype_service = ArchetypeService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Core Behavior Identification Engine...")
    mongo_service.connect()
    logger.info("All services initialized successfully")
    yield
    # Shutdown
    logger.info("Shutting down...")
    mongo_service.close()


# Create FastAPI application
app = FastAPI(
    title="Core Behavior Identification Engine",
    description="API for analyzing and clustering user behaviors",
    version="0.2.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Core Behavior Identification Engine",
        "version": "0.2.0",
        "pipeline": "cluster-centric"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "services": {
            "mongodb": "initialized",
            "embedding": "initialized",
            "archetype": "initialized",
            "clustering": "available"
        },
        "timestamp": "2025-12-04T16:20:00Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
