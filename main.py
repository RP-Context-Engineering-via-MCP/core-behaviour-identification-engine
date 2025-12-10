"""
FastAPI application for CBIE System
Main entry point for the API server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from src.config import settings
from src.api.routes import router
from src.database.mongodb_service import mongodb_service
from src.database.qdrant_service import qdrant_service
from src.services.embedding_service import embedding_service
from src.services.archetype_service import archetype_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting CBIE MVP application...")
    
    try:
        # Connect to databases
        mongodb_service.connect()
        qdrant_service.connect()
        
        # Connect to services
        embedding_service.connect()
        archetype_service.connect()
        
        logger.info("All services connected successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down CBIE MVP application...")
    
    try:
        mongodb_service.disconnect()
        qdrant_service.disconnect()
        logger.info("All services disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="CBIE MVP - Core Behavior Identification Engine",
    description="API for analyzing user behaviors and generating core behavior profiles",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["CBIE"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CBIE MVP",
        "version": "0.1.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,  # Disabled reload due to Python 3.13 multiprocessing issues
        log_level="info"
    )
