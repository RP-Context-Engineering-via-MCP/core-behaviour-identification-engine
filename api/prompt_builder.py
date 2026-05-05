"""
api/prompt_builder.py
=====================
Lightweight utility to generate the Identity Anchor Prompt from a user profile.
Decoupled from the heavy ML pipeline so the lightweight API can use it.
"""
from typing import Dict, Any

def generate_identity_prompt(profile: Dict[str, Any]) -> str:
    """
    Creates a rigid System Prompt string anchored to the user's Core Behaviour Profile.
    """
    user_id = profile.get("user_id", "Unknown")
    interests = profile.get("confirmed_interests", [])
    
    facts = [i for i in interests if i.get("status") == "Stable Fact"]
    stable = [i for i in interests if i.get("status") == "Stable"]
    emerging = [i for i in interests if i.get("status") == "Emerging"]
    archived = [i for i in interests if i.get("status") == "ARCHIVED_CORE"]
    
    # Extract topics
    def get_topics(items):
        res = []
        for item in items:
            topics = item.get("representative_topics", [])
            if topics:
                res.append(topics[0])
        return res
        
    fact_topics = get_topics(facts)
    stable_topics = get_topics(stable)
    emerging_topics = get_topics(emerging)
    archived_topics = get_topics(archived)
    
    prompt_parts = [f"--- SYSTEM IDENTITY ANCHOR FOR USER: {user_id} ---"]
    prompt_parts.append("You are speaking with a user who has following core traits and constraints.")
    
    if fact_topics:
        prompt_parts.append(f"\nCRITICAL CONSTRAINTS (Never violate):")
        for f in fact_topics:
            prompt_parts.append(f"- {f}")
            
    if stable_topics:
        prompt_parts.append(f"\nVERIFIED STABLE PREFERENCES:")
        for s in stable_topics:
            prompt_parts.append(f"- {s}")
            
    if emerging_topics:
        prompt_parts.append(f"\nEMERGING INTERESTS (Needs more verification):")
        for e in emerging_topics:
            prompt_parts.append(f"- {e}")
            
    if archived_topics:
        prompt_parts.append(f"\nARCHIVED OUTDATED HABITS (Do not use as active context):")
        for a in archived_topics:
            prompt_parts.append(f"- {a}")
            
    return "\n".join(prompt_parts)
