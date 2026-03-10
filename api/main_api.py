"""
api/main_api.py
===============
Lightweight FastAPI app for the CBIE Read-Only API service.

This is a stripped-down version of main.py that:
  - Does NOT load the heavy NLP pipeline (no PyTorch/BART/spaCy on startup)
  - Exposes only read-only endpoints: /context, /profiles, /admin (reads)
  - Runs in a tiny ~150MB container (vs the 12GB processor image)

The heavy processing (ML pipeline runs) is handled by the cbie-processor
service on port 6010 which uses the full impl-final-cbie-engine:latest image.

Start:
    uvicorn api.main_api:app --host 0.0.0.0 --port 6009
"""
from __future__ import annotations
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logger import get_logger
from api.routers import context, profiles
from api.routers import admin
from api.models import HealthResponse, RootResponse

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Application Lifespan — NO heavy pipeline init here
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lightweight startup — only connects to DB, no NLP models loaded."""
    log.info("CBIE Lightweight API starting up", extra={"stage": "STARTUP"})
    # DataAdapter (Supabase connection) is initialized lazily per-router
    log.info("API ready — accepting requests (no ML pipeline loaded)", extra={"stage": "STARTUP"})
    yield
    log.info("CBIE Lightweight API shutting down", extra={"stage": "SHUTDOWN"})


# ---------------------------------------------------------------------------
# App Instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CBIE Context API (Lightweight)",
    description=(
        "Read-only API for the CBIE. Serves pre-computed Core Behaviour Profiles "
        "from Supabase for LLM context injection. No ML pipeline runs here — "
        "use the cbie-processor service (port 6010) for pipeline execution."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Read-only routers only ─────────────────────────────────────────────────
app.include_router(context.router)   # GET /context/{user_id}
app.include_router(profiles.router)  # GET /profiles/...
app.include_router(admin.router)     # GET /admin/users/... (reads + admin run_pipeline — proxied to processor)


# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------

@app.get("/", response_model=RootResponse, tags=["Service Info"], summary="API Root")
async def root():
    return RootResponse()


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Service Info"],
    summary="Health Check",
)
async def health():
    """Always ready — no ML model to wait for."""
    return HealthResponse(
        status="ok",
        engine="CBIE-API",
        version="1.0.0",
        pipeline_ready=False,  # This service doesn't run the pipeline
    )
