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
from openai import AzureOpenAI

from data_adapter import DataAdapter

router = APIRouter(prefix="/chat", tags=["Chat Demo"])

_data_adapter = DataAdapter()

# ── Azure OpenAI client setup ──────────────────────────────────────────────────

# Use deployment name 'gpt-4o-mini' as seen in topic_discovery.py
AZURE_DEPLOYMENT = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")

def get_openai_client() -> AzureOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE")
    if not api_key or not api_base:
        raise HTTPException(status_code=500, detail="Azure OpenAI credentials not configured.")
    return AzureOpenAI(
        api_key=api_key,
        api_version=os.environ.get("OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=api_base,
    )


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


# ── Chat endpoint ─────────────────────────────────────────────────────────────

from api.routers.context import get_context

@router.post("", response_model=ChatResponse, summary="Chat with Azure OpenAI + optional CBIE context")
async def chat(req: ChatRequest):
    """
    Send a message to Azure OpenAI, with or without the CBIE identity anchor injected.
    Toggle `use_context` to see the difference in responses side-by-side.
    """
    context_text: str | None = None
    messages = []

    if req.use_context:
        try:
            # Use the official context endpoint logic to ensure we get the exact 
            # same anchor prompt that the production system would inject.
            ctx_response = await get_context(req.user_id)
            context_text = ctx_response.identity_anchor_prompt
        except HTTPException:
            # If no profile exists (404) or DB error, we fall back to no context
            context_text = None

        if context_text:
            system_instruction = (
                "You are a helpful, friendly, and highly personalised AI assistant.\n\n"
                "=== USER IDENTITY CONTEXT (provided by CBIE) ===\n"
                f"{context_text}\n"
                "=== END OF CONTEXT ===\n\n"
                "Use the above context to tailor every response to this specific user's "
                "background, interests, and constraints. Reference relevant details naturally."
            )
            messages.append({"role": "system", "content": system_instruction})
        else:
            messages.append({"role": "system", "content": "You are a helpful, friendly AI assistant."})
    else:
        messages.append({"role": "system", "content": "You are a helpful, friendly AI assistant."})

    messages.append({"role": "user", "content": req.message})

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
        )
        reply = response.choices[0].message.content or "No response from AI."
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Azure OpenAI error: {e}")

    return ChatResponse(
        reply=reply,
        user_id=req.user_id,
        use_context=req.use_context,
        context_used=context_text if req.use_context else None,
    )
