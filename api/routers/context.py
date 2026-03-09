"""
api/routers/context.py
======================
★  THE CRITICAL LLM ENDPOINT  ★

GET /context/{user_id}
    Called by the LLM orchestration layer (chat service / BAC) before every
    AI response to inject the user's fixed Identity Anchor Prompt as part of
    the system message.  No pipeline re-run is triggered here — it reads the
    latest saved profile from Supabase for near-instant latency.
"""
from __future__ import annotations
import json
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from supabase import Client

from api.models import ContextResponse
from api.dependencies import get_pipeline
from pipeline import CBIEPipeline
from data_adapter import DataAdapter

router = APIRouter(prefix="/context", tags=["LLM Context"])

# Shared DataAdapter for DB reads (no heavy NLP needed here)
_data_adapter = DataAdapter()


@router.get(
    "/{user_id}",
    response_model=ContextResponse,
    summary="Get Identity Anchor Prompt for LLM",
    description=(
        "**Critical endpoint.** Returns the pre-built Identity Anchor Prompt "
        "for the given user, ready to inject into the LLM system message. "
        "Reads from the `core_behavior_profiles` Supabase table — no pipeline "
        "re-run is triggered. Returns 404 if no profile exists yet."
    ),
)
async def get_context(user_id: str):
    """
    Fetch the stored Identity Anchor Prompt for a user.
    This is the core integration point between the CBIE and the LLM layer.
    """
    if not _data_adapter.supabase:
        raise HTTPException(status_code=503, detail="Database connection unavailable.")

    try:
        response = (
            _data_adapter.supabase
            .table("core_behavior_profiles")
            .select("user_id, confirmed_interests, updated_at")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database query failed: {e}")

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No profile found for user '{user_id}'. "
                "Run POST /pipeline/run/{user_id} to generate one."
            ),
        )

    row = response.data[0]

    # Parse confirmed_interests from the DB (may be a JSON string or list)
    raw_interests = row.get("confirmed_interests", "[]")
    if isinstance(raw_interests, str):
        try:
            interests: List = json.loads(raw_interests)
        except Exception:
            interests = []
    else:
        interests = raw_interests or []

    # Build the identity prompt in memory if it was not stored (older records)
    prompt = row.get("identity_anchor_prompt") or ""
    if not prompt and interests:
        # Regenerate on-the-fly using the pipeline helper
        pipeline: CBIEPipeline = get_pipeline()
        profile_payload = {
            "user_id": user_id,
            "confirmed_interests": interests,
            "total_raw_behaviors": row.get("total_raw_behaviors", 0),
        }
        prompt = pipeline.generate_identity_prompt(profile_payload)

    return ContextResponse(
        user_id=user_id,
        identity_anchor_prompt=prompt.replace("\n", " ").strip(),
        profile_exists=True,
        total_raw_behaviors=row.get("total_raw_behaviors", 0),
        last_updated=row.get("updated_at"),
    )
