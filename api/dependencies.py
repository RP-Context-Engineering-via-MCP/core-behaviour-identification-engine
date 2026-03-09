"""
api/dependencies.py
===================
Shared stateful resources across the entire FastAPI app:
  - CBIEPipeline singleton (heavy models loaded ONCE at startup)
  - In-memory background job registry
"""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pipeline import CBIEPipeline          # Existing engine orchestrator
from logger import get_logger
from api.models import JobProgress  # For typed progress updates

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pipeline Singleton
# ---------------------------------------------------------------------------
# The BART zero-shot model (~1.5 GB) and Azure client are created once here.
# All routers import `get_pipeline()` to access the shared instance.
# ---------------------------------------------------------------------------

_pipeline_instance: Optional[CBIEPipeline] = None


def init_pipeline() -> CBIEPipeline:
    """Called once in the app lifespan at startup."""
    global _pipeline_instance
    log.info("Initialising pipeline singleton — loading BART NLP model", extra={"stage": "STARTUP"})
    _pipeline_instance = CBIEPipeline()
    log.info("Pipeline singleton ready", extra={"stage": "STARTUP"})
    return _pipeline_instance


def get_pipeline() -> CBIEPipeline:
    """FastAPI dependency — injects the singleton pipeline."""
    if _pipeline_instance is None:
        raise RuntimeError("Pipeline not initialised. Did the app lifespan event fire?")
    return _pipeline_instance


# ---------------------------------------------------------------------------
# In-Memory Job Store
# ---------------------------------------------------------------------------
# Dictionary keyed by job_id (UUID string).
# Shape per entry:
# {
#   "job_id":       str,
#   "user_id":      str,
#   "status":       "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED",
#   "started_at":   str | None,
#   "completed_at": str | None,
#   "result":       dict | None,
#   "error":        str | None,
# }
# ---------------------------------------------------------------------------

_job_store: Dict[str, Dict[str, Any]] = {}


def create_job(user_id: str) -> str:
    """Creates a new QUEUED job and returns its job_id."""
    job_id = str(uuid.uuid4())
    _job_store[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "QUEUED",
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
        "progress": None,
    }
    log.info("Pipeline job created", extra={"job_id": job_id, "user_id": user_id, "status": "QUEUED"})
    return job_id


def update_job_progress(job_id: str, stage: str, processed: int, total: int) -> None:
    """Pushes a granular progress update into the job store while a job is RUNNING."""
    if job_id in _job_store:
        _job_store[job_id]["progress"] = {
            "stage": stage,
            "processed": processed,
            "total": total,
        }


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _job_store.get(job_id)


def update_job(job_id: str, **kwargs: Any) -> None:
    if job_id in _job_store:
        _job_store[job_id].update(kwargs)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Background Pipeline Execution
# ---------------------------------------------------------------------------

async def run_pipeline_background(job_id: str, user_id: str, force_full_run: bool = False) -> None:
    """
    Executes the heavy CBIE pipeline in a thread-pool executor so it does
    not block the FastAPI event loop.
    force_full_run=True bypasses the incremental checkpoint and reclusters everything.
    """
    update_job(job_id, status="RUNNING", started_at=now_iso())
    log.info("Pipeline job started", extra={"job_id": job_id, "user_id": user_id, "status": "RUNNING"})
    loop = asyncio.get_event_loop()

    def _progress_callback(stage: str, processed: int, total: int) -> None:
        update_job_progress(job_id, stage, processed, total)

    def _run():
        return _pipeline_instance.process_user(user_id, progress_callback=_progress_callback, force_full_run=force_full_run)

    try:
        result = await loop.run_in_executor(None, _run)
        update_job(
            job_id,
            status="COMPLETED",
            completed_at=now_iso(),
            result=result,
        )
        log.info(
            "Pipeline job completed successfully",
            extra={
                "job_id": job_id,
                "user_id": user_id,
                "status": "COMPLETED",
                "confirmed_interests": len(result.get("confirmed_interests", [])) if result else 0,
            },
        )
    except Exception as exc:
        update_job(
            job_id,
            status="FAILED",
            completed_at=now_iso(),
            error=str(exc),
        )
        log.error(
            "Pipeline job failed",
            extra={"job_id": job_id, "user_id": user_id, "status": "FAILED", "error": str(exc)},
        )
