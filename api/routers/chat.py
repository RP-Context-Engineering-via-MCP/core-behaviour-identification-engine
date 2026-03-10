"""
api/routers/chat.py
===================
Demo endpoint: chat with Gemini, optionally injecting the user's CBIE context.

POST /chat
    Body: { user_id, message, use_context }
    - If use_context=True, fetches the identity anchor prompt from core_behavior_profiles
      and injects it as a system-level instruction to Gemini.
    - If use_context=False, sends the plain message with no personalization.

This demonstrates the core value proposition of CBIE:
"The same LLM model gives dramatically different, personalized responses
 when given a user's identity anchor prompt."
"""
from __future__ import annotations
import json
import os
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

from data_adapter import DataAdapter

router = APIRouter(prefix="/chat", tags=["Chat Demo"])

_data_adapter = DataAdapter()

# ── Gemini client setup ────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)
_gemini_model = genai.GenerativeModel("gemini-1.5-flash")


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    use_context: bool = True


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    use_context: bool
    context_used: str | None = None  # The identity anchor prompt, for display


# ── Helper: fetch identity anchor prompt ──────────────────────────────────────

def _get_identity_anchor(user_id: str) -> str | None:
    """Fetch the stored identity anchor prompt for a user, or None if not found."""
    if not _data_adapter.supabase:
        return None
    try:
        resp = (
            _data_adapter.supabase
            .table("core_behavior_profiles")
            .select("identity_anchor_prompt, confirmed_interests")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None

        row = resp.data[0]
        prompt = row.get("identity_anchor_prompt") or ""

        # Fallback: build a simple prompt from interests if anchor not stored
        if not prompt:
            raw = row.get("confirmed_interests", "[]")
            interests: List = json.loads(raw) if isinstance(raw, str) else (raw or [])
            if interests:
                topics = ", ".join(
                    i.get("label", i.get("topic", "")) for i in interests[:8]
                )
                prompt = (
                    f"The user has the following confirmed core interests and traits: {topics}. "
                    "Please personalise your responses accordingly."
                )
        return prompt or None
    except Exception:
        return None


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, summary="Chat with Gemini + optional CBIE context")
async def chat(req: ChatRequest):
    """
    Send a message to Gemini, with or without the CBIE identity anchor injected.
    Toggle `use_context` to see the difference in responses side-by-side.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    context_text: str | None = None
    system_instruction: str = (
        "You are a helpful, friendly AI assistant."
    )

    if req.use_context:
        context_text = _get_identity_anchor(req.user_id)
        if context_text:
            system_instruction = (
                "You are a helpful, friendly, and highly personalised AI assistant.\n\n"
                "=== USER IDENTITY CONTEXT (provided by CBIE) ===\n"
                f"{context_text}\n"
                "=== END OF CONTEXT ===\n\n"
                "Use the above context to tailor every response to this specific user's "
                "background, interests, and constraints. Reference relevant details naturally."
            )

    try:
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=system_instruction,
        )
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(req.message)
        reply = response.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e}")

    return ChatResponse(
        reply=reply,
        user_id=req.user_id,
        use_context=req.use_context,
        context_used=context_text if req.use_context else None,
    )
