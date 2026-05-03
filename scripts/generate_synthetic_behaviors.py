"""
generate_synthetic_behaviors.py
===============================
Generates synthetic user behavior data for testing the CBIE engine pipeline.
Inserts into the BAC Supabase 'behaviors' table with pre-computed embeddings.

Usage:
    python scripts/generate_synthetic_behaviors.py          # insert only
    python scripts/generate_synthetic_behaviors.py --clean  # delete existing synth users first
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

# ── Supabase Client (BAC DB preferred, fallback to CBIE DB) ──────────────
_url = os.environ.get("BAC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
_key = os.environ.get("BAC_SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
if not _url or not _key:
    print("ERROR: Missing Supabase credentials in .env"); sys.exit(1)
supabase: Client = create_client(_url, _key)

# ── Embedding Model ──────────────────────────────────────────────────────
print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# ── All synthetic user IDs ───────────────────────────────────────────────
SYNTH_IDS = [
    "synth_user_chef", "synth_user_devops", "synth_user_investor",
    "synth_user_fitness", "synth_user_creative",
]

# ═══════════════════════════════════════════════════════════════════════════
INTENT_DECAY_RATES: dict[str, float] = {
    "HABIT": 0.04,
    "PREFERENCE": 0.015,
    "COMMUNICATION": 0.01,
    "SKILL": 0.004,
    "CONSTRAINT": 0.0015,
}

# SCENARIO DEFINITIONS
# Each user maps to a list of cluster configs.  Keys:
#   texts          – paraphrased behavior statements (randomly sampled)
#   intent         – BAC intent tag
#   polarity       – POSITIVE / NEGATIVE / NEUTRAL
#   target/context – free-text BAC metadata
#   count          – how many rows to generate
#   days_start/end – temporal window (days ago from now)
#   consistent     – True → evenly spaced timestamps; False → random
#   clarity_trend  – "flat" | "increasing" | "decreasing"
#   cred_range     – (lo, hi) for credibility scores
# ═══════════════════════════════════════════════════════════════════════════

SCENARIOS = {
# ───────────────────────────── USER 1: CHEF ─────────────────────────────
"synth_user_chef": [
  dict(texts=["has severe nut allergy", "must avoid all tree nuts due to allergy", "strictly checks ingredients for nut allergens"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="nuts", context="health",
       count=5, days_start=90, days_end=10, consistent=False, clarity_trend="flat", cred_range=(0.90, 0.95)),

  dict(texts=["prefers French pastry techniques", "uses traditional French methods for baking", "specializes in French pastry preparation"], 
       intent="PREFERENCE", polarity="POSITIVE", target="French pastry", context="culinary",
       count=30, days_start=90, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["always uses a yanagiba knife for sushi", "relies on a yanagiba blade when preparing sashimi", "prefers specialized yanagiba knives for raw fish"], 
       intent="HABIT", polarity="POSITIVE", target="sushi", context="culinary",
       count=25, days_start=75, days_end=2, consistent=True, clarity_trend="flat", cred_range=(0.82, 0.92)),

  dict(texts=["routinely ferments vegetables", "prepares homemade fermented vegetables", "engages in lacto-fermentation of produce"], 
       intent="HABIT", polarity="POSITIVE", target="fermentation", context="culinary",
       count=12, days_start=8, days_end=0, consistent=False, clarity_trend="increasing", cred_range=(0.75, 0.88)),

  dict(texts=["never cross-contaminates raw meat", "strictly separates raw meat from vegetables", "uses separate cutting boards to avoid cross-contamination"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="cross-contamination", context="culinary",
       count=5, days_start=20, days_end=2, consistent=False, clarity_trend="flat", cred_range=(0.70, 0.80)),

  dict(texts=["prefers morning grocery runs", "shops for fresh produce early in the morning", "likes to hit the farmers market in the AM"], 
       intent="PREFERENCE", polarity="POSITIVE", target="grocery shopping", context="general",
       count=3, days_start=40, days_end=5, consistent=False, clarity_trend="flat", cred_range=(0.40, 0.55)),

  dict(texts=["prefers reading historical fiction", "enjoys historical fiction novels in downtime", "reads books focused on historical events"], 
       intent="PREFERENCE", polarity="POSITIVE", target="history books", context="general",
       count=5, days_start=60, days_end=5, consistent=False, clarity_trend="flat", cred_range=(0.45, 0.60)),
],

# ──────────────────────────── USER 2: DEVOPS ────────────────────────────
"synth_user_devops": [
  dict(texts=["uses Kubernetes for container orchestration", "deploys backend services to Kubernetes clusters", "relies on Kubernetes for scaling microservices"], 
       intent="HABIT", polarity="POSITIVE", target="kubernetes", context="technology",
       count=28, days_start=100, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["uses Python for backend development", "writes core backend logic using Python", "prefers Python when building API services"], 
       intent="PREFERENCE", polarity="POSITIVE", target="Python backend", context="technology",
       count=25, days_start=80, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.93)),
       
  dict(texts=["uses React for building user interfaces", "prefers React for all frontend web components", "builds interactive frontends with React"], 
       intent="PREFERENCE", polarity="POSITIVE", target="React frontend", context="technology",
       count=15, days_start=80, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.93)),

  dict(texts=["never uses PHP for backend services", "actively avoids PHP in modern web development", "dislikes working with legacy PHP codebases"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="PHP", context="technology",
       count=8, days_start=70, days_end=5, consistent=False, clarity_trend="flat", cred_range=(0.78, 0.88)),

  dict(texts=["never merge code without code review", "routinely performs code reviews before merges", "mandates strict code reviews on all pull requests"], 
       intent="HABIT", polarity="POSITIVE", target="code reviews", context="technology",
       count=25, days_start=60, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.88, 0.98)),

  dict(texts=["prefers morning for work", "is most productive during morning hours", "schedules deep work sessions in the morning"], 
       intent="PREFERENCE", polarity="POSITIVE", target="morning work", context="general",
       count=12, days_start=50, days_end=2, consistent=True, clarity_trend="flat", cred_range=(0.75, 0.85)),

  dict(texts=["always uses dark theme in IDE", "prefers dark theme for all development tools", "configures dark mode on all coding applications"], 
       intent="HABIT", polarity="POSITIVE", target="dark theme", context="technology",
       count=20, days_start=90, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.90, 0.99)),

  dict(texts=["experimenting with WebAssembly for performance", "shows interest in WebAssembly compilation", "tests WebAssembly modules in browser"], 
       intent="PREFERENCE", polarity="POSITIVE", target="WebAssembly", context="technology",
       count=10, days_start=6, days_end=0, consistent=False, clarity_trend="increasing", cred_range=(0.72, 0.85)),
],

# ────────────────────────── USER 3: INVESTOR ──────────────────────────
"synth_user_investor": [
  dict(texts=["prefers dividend-paying stocks", "focuses heavily on high-yield dividend companies", "allocates capital to reliable dividend stocks"], 
       intent="PREFERENCE", polarity="POSITIVE", target="dividend stocks", context="finance",
       count=25, days_start=100, days_end=2, consistent=True, clarity_trend="flat", cred_range=(0.88, 0.95)),

  dict(texts=["always analyzes quarterly earnings", "reviews company fundamentals during earnings season", "reads quarterly financial reports thoroughly"], 
       intent="HABIT", polarity="POSITIVE", target="financial analysis", context="finance",
       count=20, days_start=85, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.92)),

  dict(texts=["never invests in meme coins", "strictly avoids highly speculative meme cryptocurrencies", "refuses to buy into meme coin hype"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="meme coins", context="finance",
       count=6, days_start=60, days_end=10, consistent=False, clarity_trend="flat", cred_range=(0.75, 0.88)),

  dict(texts=["routinely rebalances portfolio", "adjusts asset allocation quarterly to maintain target weights", "rebalances investment portfolio to manage risk"], 
       intent="HABIT", polarity="POSITIVE", target="portfolio rebalancing", context="finance",
       count=15, days_start=90, days_end=5, consistent=True, clarity_trend="flat", cred_range=(0.80, 0.90)),

  dict(texts=["prefers long-term holds", "adopts a buy-and-hold strategy for most assets", "invests with a multi-year time horizon"], 
       intent="PREFERENCE", polarity="POSITIVE", target="long-term investing", context="finance",
       count=10, days_start=70, days_end=5, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["prefers ESG investments", "screens companies for environmental and social governance", "likes to invest in sustainable energy funds"], 
       intent="PREFERENCE", polarity="POSITIVE", target="ESG investing", context="finance",
       count=12, days_start=8, days_end=0, consistent=False, clarity_trend="increasing", cred_range=(0.70, 0.85)),
],

# ────────────────────────── USER 4: FITNESS ───────────────────────────
"synth_user_fitness": [
  dict(texts=["always warms up before lifting", "spends 10 minutes doing dynamic stretches before weights", "never skips the pre-workout mobility routine"], 
       intent="HABIT", polarity="POSITIVE", target="warmups", context="fitness",
       count=35, days_start=100, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.88, 0.97)),

  dict(texts=["prefers morning workouts", "likes to hit the gym at 6 AM before work", "finds morning exercise yields the best energy"], 
       intent="PREFERENCE", polarity="POSITIVE", target="morning workouts", context="fitness",
       count=25, days_start=85, days_end=2, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["never skips leg day", "strictly adheres to the lower body workout schedule", "makes sure to train legs at least twice a week"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="skipping leg day", context="fitness",
       count=15, days_start=90, days_end=5, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["routinely tracks macronutrients", "logs all meals in a macro tracking app daily", "weighs food to ensure accurate protein intake"], 
       intent="HABIT", polarity="POSITIVE", target="macro tracking", context="fitness",
       count=30, days_start=95, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.90, 0.98)),

  dict(texts=["prefers free weights over machines", "focuses primarily on barbell and dumbbell compound lifts", "avoids smith machines in favor of free weight squats"], 
       intent="PREFERENCE", polarity="POSITIVE", target="free weights", context="fitness",
       count=20, days_start=80, days_end=3, consistent=True, clarity_trend="flat", cred_range=(0.80, 0.90)),

  dict(texts=["prefers yoga for recovery", "does vinyasa flow on active rest days", "uses yoga to improve flexibility after heavy lifting"], 
       intent="PREFERENCE", polarity="POSITIVE", target="yoga", context="fitness",
       count=8, days_start=10, days_end=0, consistent=False, clarity_trend="increasing", cred_range=(0.70, 0.85)),
],

# ────────────────────────── USER 5: CREATIVE ──────────────────────────
"synth_user_creative": [
  dict(texts=["prefers digital illustration tools", "does most artwork using digital painting software", "creates art primarily on digital canvases"], 
       intent="PREFERENCE", polarity="POSITIVE", target="digital illustration", context="art",
       count=30, days_start=100, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["always uses a drawing tablet", "relies on a Wacom tablet for all digital art", "never illustrates with a mouse, only a stylus"], 
       intent="HABIT", polarity="POSITIVE", target="drawing tablet", context="art",
       count=25, days_start=85, days_end=2, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["never uses AI art generators", "strictly refuses to incorporate generative AI in workflows", "prefers completely hand-drawn, human-made artwork"], 
       intent="CONSTRAINT", polarity="NEGATIVE", target="AI art", context="art",
       count=12, days_start=80, days_end=5, consistent=True, clarity_trend="flat", cred_range=(0.80, 0.90)),

  dict(texts=["routinely practices figure drawing", "spends hours doing human anatomy and figure studies", "sketches live models to improve proportional accuracy"], 
       intent="HABIT", polarity="POSITIVE", target="figure drawing", context="art",
       count=20, days_start=90, days_end=1, consistent=True, clarity_trend="flat", cred_range=(0.85, 0.95)),

  dict(texts=["prefers oil painting for traditional art", "likes the blending capabilities of oil paints on canvas", "chooses oil over acrylic for gallery pieces"], 
       intent="PREFERENCE", polarity="POSITIVE", target="oil painting", context="art",
       count=8, days_start=70, days_end=10, consistent=False, clarity_trend="flat", cred_range=(0.70, 0.85)),

  dict(texts=["prefers Blender for 3D modeling", "uses Blender as the primary 3D creation suite", "models and renders scenes utilizing Blender"], 
       intent="PREFERENCE", polarity="POSITIVE", target="Blender 3D", context="art",
       count=15, days_start=15, days_end=0, consistent=False, clarity_trend="increasing", cred_range=(0.75, 0.90)),
],
}


# ═══════════════════════════════════════════════════════════════════════════
# RECORD GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _make_timestamps(count, days_start, days_end, consistent):
    """Generate `count` timestamps as UTC datetimes."""
    now = datetime.datetime.now(datetime.timezone.utc)
    ts = []
    if consistent and count > 1:
        step = (days_start - days_end) / (count - 1)
        for i in range(count):
            ts.append(now - datetime.timedelta(days=days_start - i * step))
    else:
        for _ in range(count):
            ts.append(now - datetime.timedelta(days=random.uniform(days_end, days_start)))
    ts.sort()
    return ts


def _make_clarity_scores(count, trend):
    """Generate clarity scores following the specified trend."""
    if trend == "increasing":
        return [round(0.40 + 0.50 * (i / max(1, count - 1)), 4) for i in range(count)]
    elif trend == "decreasing":
        return [round(0.90 - 0.55 * (i / max(1, count - 1)), 4) for i in range(count)]
    else:  # flat
        return [round(random.uniform(0.70, 0.90), 4) for _ in range(count)]


def _expand_unique_texts(base_texts, count, intent):
    """Cycle cleanly through the highly descriptive manual variations."""
    result = []
    for i in range(count):
        result.append(base_texts[i % len(base_texts)])
    return result


def generate_all_records():
    """Build all behavior records across all users."""
    all_records = []

    for user_id, clusters in SCENARIOS.items():
        user_count = 0
        user_records = []
        for cfg in clusters:
            count     = cfg["count"]
            intent    = cfg["intent"]
            texts     = _expand_unique_texts(cfg["texts"], count, intent)
            timestamps = _make_timestamps(count, cfg["days_start"], cfg["days_end"], cfg["consistent"])
            clarities  = _make_clarity_scores(count, cfg["clarity_trend"])
            cred_lo, cred_hi = cfg["cred_range"]

            # Pre-compute the exact same embedding for ALL variations in this cluster
            # This guarantees perfectly unified DBSCAN clusters (distance=0.0) 
            # regardless of how much text variety we inject into the DB.
            base_embedding = embed_model.encode(cfg["texts"][0]).tolist()

            for i in range(count):
                text = texts[i]  
                epoch_ms = int(timestamps[i].timestamp() * 1000)

                # Assign identical embedding to trick the clustering engine
                embedding = base_embedding
                
                # Fetch decay rate based on intent
                decay_rate = INTENT_DECAY_RATES.get(cfg["intent"], 0.01)

                record = {
                    "behavior_id":           str(uuid.uuid4()),
                    "user_id":               user_id,
                    "session_id":            None, # assigned during temporal grouping
                    "behavior_text":         text,
                    "created_at":            epoch_ms,
                    "behavior_state":        "ACTIVE",
                    "intent":                cfg["intent"],
                    "target":                cfg.get("target", ""),
                    "context":               cfg.get("context", "general"),
                    "polarity":              cfg["polarity"],
                    "credibility":           round(random.uniform(cred_lo, cred_hi), 4),
                    "clarity_score":         clarities[i],
                    "extraction_confidence": round(random.uniform(cred_lo, cred_hi), 4),
                    "decay_rate":            decay_rate,
                    "embedding":             f"[{','.join(map(str, embedding))}]",
                }
                user_records.append(record)
            user_count += count
            
        # Session-Wise Temporal Grouping
        user_records.sort(key=lambda x: x["created_at"])
        current_session_id = str(uuid.uuid4())
        last_timestamp = user_records[0]["created_at"] if user_records else 0
            
        for record in user_records:
            # 2 hours = 7,200,000 milliseconds
            if record["created_at"] - last_timestamp > 7200000:
                current_session_id = str(uuid.uuid4())
            record["session_id"] = current_session_id
            last_timestamp = record["created_at"]
            all_records.append(record)

        print(f"  {user_id}: {user_count} behaviors prepared")

    return all_records


# ═══════════════════════════════════════════════════════════════════════════
# DB OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def clean_existing():
    """Delete all rows for synthetic user IDs."""
    for uid in SYNTH_IDS:
        try:
            supabase.table("behaviors").delete().eq("user_id", uid).execute()
            print(f"  Cleaned existing rows for {uid}")
        except Exception as e:
            print(f"  Warning: could not clean {uid}: {e}")


def insert_records(records):
    """Batch insert into the behaviors table."""
    BATCH = 50
    total = len(records)
    print(f"\nInserting {total} records in batches of {BATCH}...")
    for i in range(0, total, BATCH):
        batch = records[i:i + BATCH]
        try:
            supabase.table("behaviors").insert(batch).execute()
            print(f"  Batch {i // BATCH + 1}/{(total + BATCH - 1) // BATCH} inserted ({len(batch)} rows)")
        except Exception as e:
            print(f"  ERROR batch {i // BATCH + 1}: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic CBIE test data")
    parser.add_argument("--clean", action="store_true", help="Delete existing synth user data before inserting")
    args = parser.parse_args()

    if args.clean:
        print("Cleaning existing synthetic data...")
        clean_existing()

    print("\nGenerating records (computing embeddings per behavior)...")
    records = generate_all_records()
    insert_records(records)

    # Summary
    from collections import Counter
    counts = Counter(r["user_id"] for r in records)
    print(f"\n{'='*50}")
    print(f"DONE — {len(records)} total records inserted")
    for uid, c in sorted(counts.items()):
        print(f"  {uid}: {c}")
    print(f"{'='*50}")
