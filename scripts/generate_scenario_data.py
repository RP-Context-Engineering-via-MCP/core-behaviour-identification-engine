import os
import uuid
import json
import random
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import AzureOpenAI
from supabase import create_client

load_dotenv()

print("Initializing Azure OpenAI Client...")
openai_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_BASE")
)
embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL")

def generate_behavior_id():
    return f"beh_{uuid.uuid4().hex[:8]}"

def generate_prompt_history_id():
    return str(uuid.uuid4())

def make_record(user_id, text, intent, target, context, polarity, date_obj, decay_rate=0.015):
    return {
        "behavior_id": generate_behavior_id(),
        "user_id": user_id,
        "session_id": "default",
        "behavior_text": text,
        "credibility": round(random.uniform(0.75, 0.95), 4) if intent != "QUERY" else round(random.uniform(0.3, 0.6), 4),
        "extraction_confidence": round(random.uniform(0.75, 0.95), 4) if intent != "QUERY" else round(random.uniform(0.5, 0.7), 4),
        "clarity_score": round(random.uniform(0.8, 0.98), 4) if intent != "QUERY" else round(random.uniform(0.4, 0.7), 4),
        "linguistic_strength": round(random.uniform(0.6, 0.9), 4),
        "decay_rate": decay_rate if intent != "CONSTRAINT" else 0.0,
        "reinforcement_count": 1,
        "created_at": date_obj.isoformat() + "Z",
        "last_seen_at": date_obj.isoformat() + "Z",
        "prompt_history_ids": json.dumps([generate_prompt_history_id()]),
        "behavior_state": "ACTIVE",
        "intent": intent,
        "target": target,
        "context": context,
        "polarity": polarity,
    }

def generate_scenarios():
    all_records = []
    
    # ---------------------------------------------------------
    # Scenario 1: test_user_a (Stable Tech + Medical Fact)
    # ---------------------------------------------------------
    base_date = datetime(2024, 1, 15, 9, 0, 0)
    
    # 5x Python/FastAPI (consistent 1-2/mo over 18 months)
    python_prompts = [
        "Best practices for structuring a FastAPI project",
        "How to use SQLAlchemy 2.0 with async sessions",
        "Structuring Pydantic models for complex nested JSON",
        "How to handle JWT authentication in FastAPI",
        "Optimizing PostgreSQL queries in Python FastAPI"
    ]
    # Spaced out by ~3.5 months to cover 18 months
    for i, p in enumerate(python_prompts):
        d = base_date + timedelta(days=i * 105)
        all_records.append(make_record("test_user_a", p, "HABIT", "python backend", "tech", "POSITIVE", d))
        
    # 1x Medical Fact
    all_records.append(make_record("test_user_a", "I am severely allergic to penicillin", "CONSTRAINT", "penicillin", "health", "NEGATIVE", base_date + timedelta(days=40)))
    
    # 2x random noise
    all_records.append(make_record("test_user_a", "Current weather in Seattle", "QUERY", "weather", "general", "POSITIVE", base_date + timedelta(days=20)))
    all_records.append(make_record("test_user_a", "How long to boil a soft boiled egg", "QUERY", "egg", "general", "POSITIVE", base_date + timedelta(days=150)))

    # ---------------------------------------------------------
    # Scenario 2: test_user_b (Emerging AI + Fading Photography)
    # ---------------------------------------------------------
    # 8x photography (heavy 2024, silence 2025 + "less into it now")
    photo_prompts = [
        "Best beginner DSLR cameras 2024",
        "Understanding aperture and shutter speed",
        "How to shoot portraits in natural light",
        "Raw vs JPEG photography workflows",
        "Best Lightroom presets for landscapes",
        "Rule of thirds photography composition",
        "Which 50mm lens should I buy"
    ]
    for i, p in enumerate(photo_prompts):
        d = datetime(2024, 2, 1) + timedelta(days=i * 15) # Clustered in early 2024
        all_records.append(make_record("test_user_b", p, "HABIT", "photography hobby", "art", "POSITIVE", d))
    all_records.append(make_record("test_user_b", "I'm less into photography now, selling my camera", "PREFERENCE", "photography hobby", "art", "NEGATIVE", datetime(2025, 1, 15)))

    # 7x RAG/LLM (sparse early, dense last 6 months - say mid 2024 early, early 2025 dense)
    rag_prompts = [
        "What is Retrieval Augmented Generation",
        "How do vector databases work",
        "LangChain vs LlamaIndex comparison",
        "Building a RAG pipeline with Pinecone",
        "Optimizing chunk size for text embeddings",
        "Evaluating RAG system answers",
        "Advanced RAG techniques with hypothetical document embeddings"
    ]
    all_records.append(make_record("test_user_b", rag_prompts[0], "QUERY", "RAG systems", "tech", "POSITIVE", datetime(2024, 3, 10)))
    all_records.append(make_record("test_user_b", rag_prompts[1], "QUERY", "vector databases", "tech", "POSITIVE", datetime(2024, 8, 20)))
    for i, p in enumerate(rag_prompts[2:]):
        d = datetime(2025, 1, 1) + timedelta(days=i * 20)
        all_records.append(make_record("test_user_b", p, "HABIT", "LLM experimentation", "tech", "POSITIVE", d))

    # 10x random noise
    noise_prompts = [
        "Nearest coffee shop", "How to fix a leaky faucet", "What year did Apollo 11 land",
        "Best pizza recipe", "How to tie a tie", "Population of Japan", "Super Bowl 2023 winner",
        "How to jump start a car", "Convert 15 km to miles", "Sunset time today"
    ]
    for i, p in enumerate(noise_prompts):
        d = datetime(2024, 1, 15) + timedelta(days=i * 45)
        all_records.append(make_record("test_user_b", p, "QUERY", "random", "general", "POSITIVE", d))


    # ---------------------------------------------------------
    # Scenario 3: test_user_c (Vegan Constraint + Conflicting Queries)
    # ---------------------------------------------------------
    # 2x strict vegan/peanut allergy
    all_records.append(make_record("test_user_c", "I am strictly vegan", "CONSTRAINT", "vegan diet", "health", "POSITIVE", datetime(2024, 1, 10)))
    all_records.append(make_record("test_user_c", "I have a severe peanut allergy", "CONSTRAINT", "peanuts", "health", "NEGATIVE", datetime(2024, 1, 15)))

    # 6x vegan recipes
    vegan_prompts = [
        "Easy vegan dinner recipes",
        "High protein vegan meal prep",
        "Vegan substitutes for scrambled eggs",
        "How to make cashew cheese",
        "Best vegan restaurants near me",
        "Nut-free vegan dessert recipes"
    ]
    for i, p in enumerate(vegan_prompts):
        d = datetime(2024, 3, 1) + timedelta(days=i * 30)
        all_records.append(make_record("test_user_c", p, "PREFERENCE", "vegan meal planning", "food", "POSITIVE", d))

    # 3x ambiguous meat queries + explicit "remember I'm vegan"
    meat_prompts = [
        "How to cook a steak perfectly for my brother",
        "Best BBQ meat rub recipe for a party",
        "Where to buy good quality chicken breast"
    ]
    for i, p in enumerate(meat_prompts):
        d = datetime(2024, 6, 1) + timedelta(days=i * 40)
        all_records.append(make_record("test_user_c", p, "QUERY", "meat recipes", "food", "POSITIVE", d))
    
    all_records.append(make_record("test_user_c", "Remember I'm strictly vegan when suggesting meals", "CONSTRAINT", "vegan diet", "health", "POSITIVE", datetime(2024, 12, 1)))


    # ---------------------------------------------------------
    # Scenario 4: test_user_d (High Noise + Single Weak Signal)
    # ---------------------------------------------------------
    # 35x random noise
    for i in range(35):
        d = datetime(2024, 1, 1) + timedelta(days=i * 12)
        all_records.append(make_record("test_user_d", f"Random query about weather, facts, or jokes number {i}", "QUERY", "random", "general", "POSITIVE", d))
    
    # 4x barefoot running
    run_prompts = [
        "Barefoot running technique for beginners",
        "Vibram FiveFingers transition guide",
        "Forefoot strike running form check",
        "Minimalist running shoe reviews"
    ]
    for i, p in enumerate(run_prompts):
        d = datetime(2025, 2, 1) + timedelta(days=i * 7) # highly recent and clustered
        all_records.append(make_record("test_user_d", p, "HABIT", "barefoot running", "fitness", "POSITIVE", d))


    # ---------------------------------------------------------
    # Scenario 5: test_user_e (Polarity Conflict Test)
    # ---------------------------------------------------------
    # 5x "loves coffee" (POSITIVE)
    coffee_prompts = [
        "I absolutely love my morning espresso",
        "Best specialty coffee beans to order online",
        "How to dial in a new bag of light roast coffee",
        "Upgrading to a dual boiler espresso machine",
        "Latte art pouring techniques"
    ]
    for i, p in enumerate(coffee_prompts):
        d = datetime(2024, 1, 15) + timedelta(days=i * 40)
        all_records.append(make_record("test_user_e", p, "PREFERENCE", "coffee", "food", "POSITIVE", d))

    # 4x "hates coffee now, switched to tea" (NEGATIVE, later dates)
    tea_prompts = [
        "I hate coffee now, gives me the jitters",
        "Switching from coffee to matcha green tea",
        "Best loose leaf oolong tea vendors",
        "How to brew sencha green tea properly"
    ]
    for i, p in enumerate(tea_prompts):
        d = datetime(2025, 1, 10) + timedelta(days=i * 20)
        # We classify the first one as NEGATIVE polarity towards coffee
        if i == 0:
            all_records.append(make_record("test_user_e", p, "PREFERENCE", "coffee", "food", "NEGATIVE", d))
        else:
            all_records.append(make_record("test_user_e", p, "PREFERENCE", "tea", "food", "POSITIVE", d))

    return all_records

def attach_embeddings(records):
    print(f"Generating Azure embeddings for {len(records)} behaviors...")
    texts = [r["behavior_text"] for r in records]
    
    embeddings = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        attempts = 0
        while attempts < 3:
            try:
                response = openai_client.embeddings.create(input=batch, model=embedding_model)
                embeddings.extend([r.embedding for r in response.data])
                break
            except Exception as e:
                attempts += 1
                wait_time = attempts * 5
                print(f"Azure OpenAI Error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

    for i, emb in enumerate(embeddings):
        emb_str = "[" + ",".join(str(float(v)) for v in emb) + "]"
        records[i]["embedding"] = emb_str
    
    return records

def main():
    print("=" * 60)
    print("CBIE Scenario Test Data Generator")
    print("=" * 60)
    
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    sb = create_client(url, key)
    
    print("Generating records...")
    records = generate_scenarios()
    
    print("Generating embeddings...")
    records = attach_embeddings(records)
    
    print("\nSeeding data into Supabase 'behaviors' table...")
    try:
        batch_size = 20
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            sb.table("behaviors").insert(batch).execute()
            print(f"  Inserted batch {i // batch_size + 1} ({len(batch)} records)")
        print(f"\nSuccessfully seeded {len(records)} records!")
    except Exception as e:
        print(f"ERROR seeding data: {e}")

if __name__ == "__main__":
    main()
