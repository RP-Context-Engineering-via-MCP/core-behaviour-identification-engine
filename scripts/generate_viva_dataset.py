"""
generate_viva_dataset.py
========================
Generates a highly-curated synthetic user behavior dataset specifically
designed to demonstrate the core capabilities of the CBIE engine during the Viva.

Capabilities Demonstrated:
1. Standard Consistency (Gini)
2. Heuristic Consistency (Aggregated Reinforcement)
3. Trend Detection (Mann-Kendall)
4. Noise Filtering
"""

import os
import sys
import uuid
import random
import argparse
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

load_dotenv()

# ── Supabase Client ──────────────────────────────────────────────────────
_url = os.environ.get("BAC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
_key = os.environ.get("BAC_SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if not _url or not _key:
    print("ERROR: Missing Supabase credentials in .env"); sys.exit(1)
supabase: Client = create_client(_url, _key)

# ── Embedding Model ──────────────────────────────────────────────────────
print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

USER_ID = "demo_user_001"

# ═══════════════════════════════════════════════════════════════════════════
# VIVA SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    # 1. Standard Habit (Proves Gini & Frequency)
    # High frequency, evenly spaced over time.
    dict(
        topic="Drinks black coffee in the morning",
        texts=["always drinks black coffee in the AM", "has a morning black coffee", "prefers black coffee before work"],
        intent="HABIT", polarity="POSITIVE", context="lifestyle",
        row_count=15, reinforcement_per_row=1, days_start=30, days_end=1, 
        consistent_time=True, clarity_trend="flat", cred_range=(0.85, 0.95)
    ),

    # 2. Aggregated Habit (Proves New Heuristic Logic)
    # A single row but with a massive reinforcement count.
    # Without the heuristic, this would be penalized by Gini (or fail).
    dict(
        topic="Uses dark mode theme",
        texts=["always uses dark theme on IDE", "prefers dark mode interfaces", "sets all apps to dark mode"],
        intent="PREFERENCE", polarity="POSITIVE", context="technology",
        row_count=1, reinforcement_per_row=25, days_start=5, days_end=5, 
        consistent_time=False, clarity_trend="flat", cred_range=(0.90, 0.99)
    ),

    # 3. Emerging Trend (Proves Mann-Kendall)
    # Moderate frequency, but increasing clarity scores.
    dict(
        topic="Learning Rust programming",
        texts=["is studying Rust programming language", "practicing Rust coding", "learning memory safety with Rust"],
        intent="SKILL", polarity="POSITIVE", context="technology",
        row_count=8, reinforcement_per_row=1, days_start=14, days_end=1, 
        consistent_time=False, clarity_trend="increasing", cred_range=(0.70, 0.95)
    ),

    # 4. Noise (Proves Filtering)
    # Low frequency, single timestamp. Realistic BAC extraction but never repeated.
    dict(
        topic="Tried Obsidian for note-taking",
        texts=["prefers using Obsidian for a new project", "experimented with Obsidian note-taking", "wants to use Obsidian for markdown notes"],
        intent="PREFERENCE", polarity="POSITIVE", context="productivity",
        row_count=1, reinforcement_per_row=1, days_start=10, days_end=10, 
        consistent_time=False, clarity_trend="flat", cred_range=(0.80, 0.90)
    )
]

def _make_timestamps(count, days_start, days_end, consistent):
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = []
    if count == 1:
        return [now - datetime.timedelta(days=days_start)]
        
    if consistent:
        step = (days_start - days_end) / (count - 1)
        for i in range(count):
            ts.append(now - datetime.timedelta(days=days_start - i * step))
    else:
        for _ in range(count):
            ts.append(now - datetime.timedelta(days=random.uniform(days_end, days_start)))
    ts.sort()
    return ts

def _make_clarity_scores(count, trend):
    if count == 1:
        return [0.85]
    if trend == "increasing":
        return [round(0.40 + 0.50 * (i / max(1, count - 1)), 4) for i in range(count)]
    elif trend == "decreasing":
        return [round(0.90 - 0.55 * (i / max(1, count - 1)), 4) for i in range(count)]
    else:  # flat
        return [round(random.uniform(0.70, 0.90), 4) for _ in range(count)]

def generate_records():
    all_records = []
    
    for cfg in SCENARIOS:
        count = cfg["row_count"]
        texts = [cfg["texts"][i % len(cfg["texts"])] for i in range(count)]
        timestamps = _make_timestamps(count, cfg["days_start"], cfg["days_end"], cfg["consistent_time"])
        clarities = _make_clarity_scores(count, cfg["clarity_trend"])
        cred_lo, cred_hi = cfg["cred_range"]
        
        # Exact same embedding to trick clustering into perfect grouping
        base_embedding = embed_model.encode(cfg["texts"][0]).tolist()
        
        for i in range(count):
            record = {
                "behavior_id": str(uuid.uuid4()),
                "user_id": USER_ID,
                "session_id": str(uuid.uuid4()),  # Simple session assignment
                "behavior_text": texts[i],
                "created_at": int(timestamps[i].timestamp() * 1000),
                "behavior_state": "ACTIVE",
                "intent": cfg["intent"],
                "target": cfg["topic"],
                "context": cfg["context"],
                "polarity": cfg["polarity"],
                "credibility": round(random.uniform(cred_lo, cred_hi), 4),
                "clarity_score": clarities[i],
                "extraction_confidence": round(random.uniform(cred_lo, cred_hi), 4),
                "decay_rate": 0.01,
                "embedding": f"[{','.join(map(str, base_embedding))}]",
                "reinforcement_count": cfg["reinforcement_per_row"]
            }
            all_records.append(record)
            
    print(f"Generated {len(all_records)} behavior records for {USER_ID}")
    return all_records

def clean_existing():
    try:
        supabase.table("behaviors").delete().eq("user_id", USER_ID).execute()
        print(f"Cleaned existing rows for {USER_ID}")
    except Exception as e:
        print(f"Warning: could not clean {USER_ID}: {e}")

def insert_records(records):
    try:
        supabase.table("behaviors").insert(records).execute()
        print("Insert complete.")
    except Exception as e:
        print(f"ERROR inserting records: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    if args.clean:
        clean_existing()

    records = generate_records()
    insert_records(records)
