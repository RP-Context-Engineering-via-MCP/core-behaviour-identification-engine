"""
api/routers/pipeline.py
=======================
Endpoints to trigger and monitor CBIE analysis pipeline runs.

POST /pipeline/run/{user_id}
    Kick off a full CBIE analysis for a user.  Returns immediately with a
    job_id — the heavy work runs in a background thread.

GET  /pipeline/status/{job_id}
    Poll for the status and (when done) the full result profile.
"""
from __future__ import annotations
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.models import PipelineRunResponse, PipelineStatusResponse
from api.dependencies import (
    get_pipeline,
    create_job,
    get_job,
    run_pipeline_background,
)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.post(
    "/run/{user_id}",
    response_model=PipelineRunResponse,
    status_code=202,
    summary="Trigger CBIE Pipeline Run",
    description=(
        "Queues a full CBIE analysis pipeline run for the specified user. "
        "The job runs in the background (the BART model can take several minutes). "
        "Use `GET /pipeline/status/{job_id}` to poll for completion."
    ),
)
async def trigger_pipeline_run(user_id: str, background_tasks: BackgroundTasks, force_full_run: str = "false"):
    """
    Accepts a user_id, creates a background job, and returns immediately.
    The pipeline runs asynchronously — the LLM/frontend should poll for status.
    Set force_full_run=true to bypass the incremental checkpoint and recluster everything.
    """
    _force = force_full_run.strip().lower() in ("true", "1", "yes")
    # Ensure the pipeline singleton is available before queuing
    get_pipeline()  # raises 500 if not initialised

    job_id = create_job(user_id)

    # Schedule the heavy pipeline to run in the background
    background_tasks.add_task(run_pipeline_background, job_id, user_id, _force)

    return PipelineRunResponse(
        job_id=job_id,
        status="QUEUED",
        user_id=user_id,
        message=(
            f"Pipeline run queued for user '{user_id}'. "
            f"Poll GET /pipeline/status/{job_id} for progress."
        ),
    )


@router.get(
    "/status/{job_id}",
    response_model=PipelineStatusResponse,
    summary="Get Pipeline Job Status",
    description=(
        "Poll the status of a previously triggered pipeline run. "
        "Possible statuses: QUEUED, RUNNING, COMPLETED, FAILED."
    ),
)
async def get_pipeline_status(job_id: str):
    """
    Returns the current status of a pipeline job.
    On COMPLETED, includes the full Core Behaviour Profile JSON in `result`.
    """
    job = get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Check your job_id.",
        )

    return PipelineStatusResponse(
        job_id=job["job_id"],
        user_id=job["user_id"],
        status=job["status"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        result=job.get("result"),
        error=job.get("error"),
    )
