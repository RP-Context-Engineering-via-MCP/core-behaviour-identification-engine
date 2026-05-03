"""
generate_demo_user.py
=====================
Generates one realistic demo user ("demo_user_alex") with ~60 behaviours
covering all three CBIE behaviour categories plus noise:

  - FACTS / CRITICAL  (~8)  — hard constraints (dietary, health, lifestyle)
  - STABLE             (~25) — long-running, high-frequency interests
  - EMERGING           (~15) — recent, growing interest area
  - NOISE              (~12) — irrelevant one-off queries

Embeddings use the local sentence-transformers model (384-dim).
Data is inserted DIRECTLY into the BAC Supabase behaviours table.
Existing records for "demo_user_alex" are cleared first.

Usage:
    ..\venv\Scripts\python generate_demo_user.py
"""
import os
import sys
import uuid
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ─── Config ───────────────────────────────────────────────────────────────────
USER_ID    = "demo_user_alex"
NOW        = datetime.now(timezone.utc)
START_DATE = NOW - timedelta(days=730)   # 2 years of history

# ─── DB client ────────────────────────────────────────────────────────────────
supabase = create_client(
    os.environ["BAC_SUPABASE_URL"],
    os.environ["BAC_SUPABASE_KEY"],
)
model = SentenceTransformer("all-MiniLM-L6-v2")

# ─── Persona: Alex — Senior Python/ML Engineer, Health-Conscious ─────────────
#
# FACTS (hard constraints — never change, must always be respected):
#   • Has Type 1 diabetes → must avoid high-glycaemic foods
#   • Vegetarian — does not eat meat or seafood
#   • Lactose intolerant — avoids dairy
#   • Works remotely from Sri Lanka
#
# STABLE (consistent deep interests, 12-24 months):
#   • Python backend development (FastAPI, SQLAlchemy, Pydantic)
#   • Machine learning engineering (scikit-learn, feature engineering, MLOps)
#   • Supabase & PostgreSQL — primary DB stack
#   • Running / marathon training
#   • Personal finance & FIRE movement
#
# EMERGING (last 3-6 months, growing signal):
#   • Rust programming language
#   • LLM application development (LangChain, RAG pipelines)
#
# NOISE (random off-topic queries):
#   • Sport scores, recipe questions, celebrity news, etc.

BEHAVIORS: list[dict] = []

def ts_ms(dt: datetime) -> int:
    """Datetime → Unix milliseconds (bigint for Supabase)."""
    return int(dt.timestamp() * 1000)

def spread(start_offset_days: int, end_offset_days: int, count: int) -> list[int]:
    """Return `count` timestamps (ms) spread between two relative day offsets from NOW."""
    lo = NOW - timedelta(days=start_offset_days)
    hi = NOW - timedelta(days=end_offset_days)
    span = (hi - lo).total_seconds()
    return sorted([
        ts_ms(lo + timedelta(seconds=random.uniform(0, span)))
        for _ in range(count)
    ])

def add(text: str, intent: str, context: str, polarity: str,
        clarity: float, credibility: float, decay: float,
        ts_ms_val: int, state: str = "ACTIVE"):
    BEHAVIORS.append({
        "behavior_id":           str(uuid.uuid4()),
        "session_id":            str(uuid.uuid4()),
        "user_id":               USER_ID,
        "behavior_text":         text,
        "embedding":             None,          # filled below
        "credibility":           round(credibility, 4),
        "clarity_score":         round(clarity, 4),
        "extraction_confidence": round((clarity + credibility) / 2, 4),
        "intent":                intent,
        "target":                "general",
        "context":               context,
        "polarity":              polarity,
        "created_at":            ts_ms_val,
        "behavior_state":        state,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 1. FACTS  (~8)  — spread uniformly across full 2-year span
# ─────────────────────────────────────────────────────────────────────────────
fact_ts = spread(730, 0, 8)

fact_behaviors = [
    ("Has Type 1 diabetes and requires low-glycaemic food choices",                           "health"),
    ("Is a strict vegetarian and does not eat meat, poultry, or seafood",                     "lifestyle"),
    ("Is lactose intolerant and must avoid all dairy products including milk and cheese",      "health"),
    ("Works fully remotely as a software engineer based in Sri Lanka",                         "identity"),
    ("Requires insulin management and blood sugar monitoring throughout the day",               "health"),
    ("Does not consume alcohol for health and personal reasons",                               "lifestyle"),
    ("Follows a high-protein plant-based diet to support marathon training",                   "health"),
    ("Is sensitive to artificial food additives and prefers whole natural ingredients",        "health"),
]

for (text, ctx), ts in zip(fact_behaviors, fact_ts):
    add(text, intent="CONSTRAINT", context=ctx, polarity="NEUTRAL",
        clarity=0.95, credibility=0.97, decay=0.0, ts_ms_val=ts)


# ─────────────────────────────────────────────────────────────────────────────
# 2. STABLE  (~25)  — spread across full 2-year span, high regularity
# ─────────────────────────────────────────────────────────────────────────────
stable_texts = [
    # Python / FastAPI
    ("Builds production REST APIs using FastAPI with Pydantic data validation",               "tech"),
    ("Implements async database access patterns using SQLAlchemy 2.0 in Python",              "tech"),
    ("Configures FastAPI dependency injection for shared database sessions",                   "tech"),
    ("Writes unit and integration tests for FastAPI endpoints using pytest and httpx",         "tech"),
    ("Designs Pydantic v2 models for request and response serialization",                     "tech"),
    ("Uses Python type hints and mypy for static type safety in backend code",                "tech"),
    ("Deploys Python FastAPI services with uvicorn behind an nginx reverse proxy",            "tech"),
    # ML Engineering
    ("Designs feature engineering pipelines for tabular ML datasets using scikit-learn",     "tech"),
    ("Uses SHAP values to explain machine learning model predictions",                        "tech"),
    ("Builds model evaluation dashboards to track precision, recall, and AUC metrics",       "tech"),
    ("Implements cross-validation strategies to prevent overfitting on small datasets",       "tech"),
    ("Explores MLflow for experiment tracking and model versioning",                          "tech"),
    # Supabase / PostgreSQL
    ("Uses Supabase as primary database backend for Python web applications",                 "tech"),
    ("Optimises PostgreSQL queries with EXPLAIN ANALYSE and index tuning",                    "tech"),
    ("Designs row-level security policies in Supabase for multi-tenant applications",        "tech"),
    ("Uses pg_vector extension for storing and querying semantic embeddings",                 "tech"),
    # Running / Fitness
    ("Trains for half-marathon using structured weekly mileage build-up programmes",          "fitness"),
    ("Tracks running cadence, heart rate zones, and VO2 max via Garmin watch",               "fitness"),
    ("Follows a high-protein vegetarian nutrition plan to support endurance training",        "fitness"),
    ("Monitors blood sugar carefully before and after long distance training runs",           "fitness"),
    ("Participates in local park run events every Saturday morning in Colombo",              "fitness"),
    # Personal Finance / FIRE
    ("Invests a fixed percentage of salary monthly into index funds for financial independence", "finance"),
    ("Tracks monthly spending and savings rate using a personal budget spreadsheet",          "finance"),
    ("Studies the FIRE movement and plans for early retirement through passive income",       "finance"),
    ("Evaluates Sri Lanka CSE stocks alongside global ETFs for portfolio diversification",    "finance"),
]

stable_ts = spread(730, 30, len(stable_texts))
for (text, ctx), ts in zip(stable_texts, stable_ts):
    add(text, intent=random.choice(["HABIT", "PREFERENCE"]), context=ctx, polarity="POSITIVE",
        clarity=random.uniform(0.80, 0.97), credibility=random.uniform(0.82, 0.96),
        decay=0.012, ts_ms_val=ts)


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMERGING  (~15)  — last 3-6 months only, increasing frequency
# ─────────────────────────────────────────────────────────────────────────────
emerging_texts = [
    # Rust
    ("Started learning Rust programming language via the official Rust book",                 "tech"),
    ("Experimenting with Rust's ownership and borrowing model for memory safety",             "tech"),
    ("Building a small CLI tool in Rust as a first hands-on project",                        "tech"),
    ("Comparing Rust performance with Python for data processing pipelines",                  "tech"),
    ("Exploring Rust async runtime with Tokio for building concurrent services",              "tech"),
    ("Evaluating whether Rust could replace Python for CPU-intensive ML preprocessing",       "tech"),
    # LLM Applications
    ("Building a RAG pipeline using LangChain and Supabase vector search",                   "tech"),
    ("Evaluating LLM output quality with RAGAS framework for RAG accuracy",                  "tech"),
    ("Experimenting with OpenAI function calling for structured data extraction",             "tech"),
    ("Studying prompt engineering techniques to improve LLM reasoning reliability",           "tech"),
    ("Integrating a local Ollama LLM into a Python FastAPI backend for inference",           "tech"),
    ("Asks about best practices for chunking documents for RAG retrieval",                   "tech"),
    ("Compares embedding models for semantic search quality in RAG applications",             "tech"),
    ("Reading about multi-agent LLM architectures and tool-use frameworks",                   "tech"),
    ("Building a prototype personal knowledge assistant using LLM and vector DB",            "tech"),
]

emerging_ts = spread(180, 0, len(emerging_texts))
for (text, ctx), ts in zip(emerging_texts, emerging_ts):
    add(text, intent=random.choice(["QUERY", "PREFERENCE"]), context=ctx, polarity="POSITIVE",
        clarity=random.uniform(0.65, 0.85), credibility=random.uniform(0.68, 0.88),
        decay=0.03, ts_ms_val=ts)


# ─────────────────────────────────────────────────────────────────────────────
# 4. NOISE  (~12)  — random one-off queries, no clear pattern
# ─────────────────────────────────────────────────────────────────────────────
noise_texts = [
    "What is the weather in Colombo tomorrow?",
    "Best Netflix series to watch this weekend",
    "How to remove a password from a PDF file",
    "What time is the Champions League final?",
    "How do I fix a slow kitchen tap?",
    "Current exchange rate of USD to LKR",
    "Best noise-cancelling headphones under 10000 rupees",
    "How long does a car tyre last on average?",
    "Latest news from Sri Lanka parliamentary elections",
    "How to grow tomatoes in a home garden",
    "What is the capital city of Norway?",
    "Fastest route from Colombo to Kandy by train",
]

noise_ts = spread(730, 0, len(noise_texts))
for text, ts in zip(noise_texts, noise_ts):
    add(text, intent="QUERY", context="general", polarity="NEUTRAL",
        clarity=random.uniform(0.30, 0.55), credibility=random.uniform(0.35, 0.60),
        decay=0.07, ts_ms_val=ts)


# ─────────────────────────────────────────────────────────────────────────────
# Embed + Insert
# ─────────────────────────────────────────────────────────────────────────────
print(f"=== Demo User Generator: {USER_ID} ===")
print(f"  Total behaviours: {len(BEHAVIORS)}")
print(f"  Facts/Critical : {sum(1 for b in BEHAVIORS if b['intent'] == 'CONSTRAINT')}")
print(f"  Stable          : 25")
print(f"  Emerging        : 15")
print(f"  Noise           : 12")

print("\nGenerating embeddings...")
texts = [b["behavior_text"] for b in BEHAVIORS]
embeddings = model.encode(texts)
for b, emb in zip(BEHAVIORS, embeddings):
    b["embedding"] = emb.tolist()
print(f"  ✓ {len(embeddings)} embeddings generated (dim={len(embeddings[0])})")

print(f"\nClearing existing data for {USER_ID}...")
supabase.table("behaviors").delete().eq("user_id", USER_ID).execute()

print("Inserting records...")
chunk_size = 20
for i in range(0, len(BEHAVIORS), chunk_size):
    chunk = BEHAVIORS[i:i + chunk_size]
    supabase.table("behaviors").insert(chunk).execute()
    print(f"  Inserted chunk {i // chunk_size + 1}/{-(-len(BEHAVIORS) // chunk_size)}"
          f" ({len(chunk)} records)")

print(f"\n✓ Done — {len(BEHAVIORS)} behaviour records seeded for '{USER_ID}'")
print("  You can now run the CBIE pipeline on this user from the Admin Dashboard.")
