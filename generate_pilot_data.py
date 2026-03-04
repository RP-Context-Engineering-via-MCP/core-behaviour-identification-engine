import os
import uuid
import json
import random
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# Configuration
NUM_USERS = 10
BEHAVIORS_PER_USER = 300
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2026, 3, 1)
TOTAL_DAYS = (END_DATE - START_DATE).days

# Personas definition
PERSONAS = [
    {
        "user_id": "pilot_user_1",
        "description": "Python Backend Dev",
        "facts": ["Sri Lanka dev"],
        "stable": ["Python backend", "FastAPI"],
        "emerging": ["Asyncio"],
        "archived": ["Flask"]
    },
    {
        "user_id": "pilot_user_2",
        "description": "Banking Tech",
        "facts": ["Finacle expert"],
        "stable": ["SWIFT MT/MX", "IBM MQ"],
        "emerging": ["OIC integration"],
        "archived": []
    },
    {
        "user_id": "pilot_user_3",
        "description": "AI Researcher",
        "facts": [],
        "stable": ["RAG systems", "NLP"],
        "emerging": ["pgvector"],
        "archived": []
    },
    {
        "user_id": "pilot_user_4",
        "description": "Stock Investor",
        "facts": ["risk averse"],
        "stable": ["portfolio mgmt"],
        "emerging": ["AI predictions"],
        "archived": []
    },
    {
        "user_id": "pilot_user_5",
        "description": "Vegan Diabetic",
        "facts": ["vegan", "diabetic", "nut allergy"],
        "stable": ["plant-based diet"],
        "emerging": [],
        "archived": []
    },
    {
        "user_id": "pilot_user_6",
        "description": "Fragrance Fan",
        "facts": [],
        "stable": ["luxury perfumes"],
        "emerging": ["Oud fragrances"],
        "archived": []
    },
    {
        "user_id": "pilot_user_7",
        "description": "Oracle Certs",
        "facts": [],
        "stable": ["Oracle Cloud", "OIC"],
        "emerging": [],
        "archived": ["Java banking"]
    },
    {
        "user_id": "pilot_user_8",
        "description": "SysAdmin",
        "facts": ["RHEL expert"],
        "stable": ["Linux admin", "MQ clusters"],
        "emerging": [],
        "archived": []
    },
    {
        "user_id": "pilot_user_9",
        "description": "Finance Analyst",
        "facts": [],
        "stable": ["financial statements"],
        "emerging": ["LLM analysis"],
        "archived": []
    },
    {
        "user_id": "pilot_user_10",
        "description": "Hobbyist",
        "facts": [],
        "stable": ["AI papers"],
        "emerging": [],
        "archived": [],
        "is_hobbyist": True
    }
]

def generate_mock_embedding():
    # 3072-dimensional vector with values in [-0.02, 0.02]
    vec = np.random.uniform(-0.02, 0.02, 3072)
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"

def generate_behavior_text(trait, category):
    templates = {
        "facts": [
            f"is identified as {trait}",
            f"has the attribute of being {trait}",
            f"explicitly noted as {trait}",
            f"matches profile of {trait}",
            f"is an established {trait}"
        ],
        "stable": [
            f"frequently works with {trait}",
            f"prefers {trait} over alternatives",
            f"shows consistent interest in {trait}",
            f"regularly focuses on {trait}",
            f"has strong preference for {trait}",
            f"consistently utilizes {trait}",
            f"demonstrates expertise in {trait}",
            f"heavily relies on {trait}"
        ],
        "emerging": [
            f"is currently exploring {trait}",
            f"shows new interest in {trait}",
            f"recently started looking into {trait}",
            f"is evaluating {trait} capabilities",
            f"shows emerging engagement with {trait}",
            f"is asking questions about {trait}"
        ],
        "archived": [
            f"previously used {trait}",
            f"has past history with {trait}",
            f"focused on {trait} in the past",
            f"shows declining interest in {trait}",
            f"migrating away from {trait}"
        ],
        "noise": []  # handled dynamically
    }
    if category == "noise":
        noise_verbs = ["asked about", "briefly mentioned", "shows passing interest in", "inquired regarding"]
        return f"{random.choice(noise_verbs)} {fake.bs().lower()}"
    else:
        return random.choice(templates[category])

def get_timestamps(pattern, count):
    if count <= 0:
        return []
    
    if pattern == "stable":
        # Uniformly distributed over 2 years
        deltas = np.random.uniform(0, TOTAL_DAYS, count)
    elif pattern == "emerging":
        # Dense in the last 6 months (approx 180 days)
        deltas = np.random.uniform(TOTAL_DAYS - 180, TOTAL_DAYS, count)
    elif pattern == "archived":
        # Burst in 2024, silence in 2025
        # 2024 is the first 365 days
        deltas = np.random.uniform(0, 365, count)
    else: # facts and noise
        # Scattered randomly
        deltas = np.random.uniform(0, TOTAL_DAYS, count)
        
    dates = sorted([START_DATE + timedelta(days=float(d)) for d in deltas])
    return [d.isoformat() + "Z" for d in dates]

def generate_data():
    behaviors_data = []
    ground_truth_data = []
    
    print("Generating synthetic pilot data...")
    for p in PERSONAS:
        user_id = p["user_id"]
        
        # Proportions
        if p.get("is_hobbyist"):
            target_counts = {
                "stable": 150,
                "emerging": 0,
                "archived": 0,
                "facts": 0,
                "noise": 150
            }
        else:
            target_counts = {
                "stable": int(BEHAVIORS_PER_USER * 0.40),
                "emerging": int(BEHAVIORS_PER_USER * 0.20),
                "archived": int(BEHAVIORS_PER_USER * 0.15),
                "facts": int(BEHAVIORS_PER_USER * 0.10),
                "noise": int(BEHAVIORS_PER_USER * 0.15)
            }
        
        # Distribute missing categories to noise if necessary
        for cat in ["stable", "emerging", "archived", "facts"]:
            if len(p[cat]) == 0 and target_counts[cat] > 0:
                target_counts["noise"] += target_counts[cat]
                target_counts[cat] = 0
                
        # Generate Ground Truths
        for cat in ["stable", "emerging", "archived", "facts"]:
            for trait in p[cat]:
                ground_truth_data.append({
                    "user_id": user_id,
                    "trait": trait,
                    "status": cat.upper(),
                    "is_fact": cat == "facts"
                })
        
        # Generate Behaviors
        for cat in ["stable", "emerging", "archived", "facts", "noise"]:
            count = target_counts[cat]
            if count <= 0:
                continue
                
            traits = p.get(cat, ["noise"]) if cat != "noise" else ["noise"]
            traits_iter = (traits * (count // len(traits) + 1))[:count]
            random.shuffle(traits_iter)
            
            timestamps = get_timestamps(cat, count)
            
            for i, trait in enumerate(traits_iter):
                behavior_id = str(uuid.uuid4())
                b_text = generate_behavior_text(trait, cat)
                
                if cat == "noise":
                    cred = round(random.uniform(0.3, 0.6), 4)
                    clar = round(random.uniform(0.3, 0.6), 4)
                    conf = round(random.uniform(0.3, 0.6), 4)
                    intent = "QUERY"
                    target = b_text.split()[0].lower() # mock target
                    context = "general"
                elif cat == "facts":
                    cred = round(random.uniform(0.8, 1.0), 4)
                    clar = round(random.uniform(0.8, 1.0), 4)
                    conf = round(random.uniform(0.8, 1.0), 4)
                    intent = "CONSTRAINT"
                    target = trait
                    context = "lifestyle"
                else:
                    cred = round(random.uniform(0.7, 1.0), 4)
                    clar = round(random.uniform(0.7, 1.0), 4)
                    conf = round(random.uniform(0.7, 1.0), 4)
                    intent = random.choice(["PREFERENCE", "HABIT", "QUERY"])
                    target = trait
                    context = "tech" if cat in ["stable", "emerging", "archived"] else "general"

                behaviors_data.append({
                    "behavior_id": behavior_id,
                    "user_id": user_id,
                    "behavior_text": b_text,
                    "embedding": generate_mock_embedding(),
                    "credibility": cred,
                    "clarity_score": clar,
                    "extraction_confidence": conf,
                    "intent": intent,
                    "target": target,
                    "context": context,
                    "polarity": "POSITIVE",
                    "created_at": timestamps[i],
                    "decay_rate": 0.015 if cat != "facts" else 0.0,
                    "reinforcement_count": random.randint(1, 5),
                    "behavior_state": "ACTIVE"
                })

        print(f"  User {user_id}: {sum(target_counts.values())} behaviors, " + 
              f"{100-target_counts['noise']/300*100:.0f}% signal coverage")

    # To DataFrame
    behaviors_df = pd.DataFrame(behaviors_data)
    gt_df = pd.DataFrame(ground_truth_data)
    
    # Reorder columns explicitly to match schema expectation
    cols = ["behavior_id", "user_id", "behavior_text", "embedding", "credibility", 
            "clarity_score", "extraction_confidence", "intent", "target", "context", 
            "polarity", "created_at", "decay_rate", "reinforcement_count", "behavior_state"]
    behaviors_df = behaviors_df[cols]

    return behaviors_df, gt_df

def save_outputs(behaviors_df, gt_df):
    out_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. behaviours_pilot.csv
    b_csv_path = os.path.join(out_dir, "behaviors_pilot.csv")
    behaviors_df.to_csv(b_csv_path, index=False)
    print(f"\nSaved {len(behaviors_df)} rows to {b_csv_path}")
    
    # 2. ground_truth_pilot.csv
    gt_csv_path = os.path.join(out_dir, "ground_truth_pilot.csv")
    gt_df.to_csv(gt_csv_path, index=False)
    print(f"Saved {len(gt_df)} rows to {gt_csv_path}")
    
    # 3. behaviours_pilot.sql
    sql_path = os.path.join(out_dir, "behaviors_pilot.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- CBIE Pilot Eval Data\n")
        
        # Write inserts in chunks of 100 for better performace
        chunk_size = 100
        total_rows = len(behaviors_df)
        for i in range(0, total_rows, chunk_size):
            chunk = behaviors_df.iloc[i:i+chunk_size]
            values_list = []
            for _, row in chunk.iterrows():
                clean_text = row['behavior_text'].replace("'", "''")
                val_str = f"('{row['behavior_id']}', '{row['user_id']}', '{clean_text}', '{row['embedding']}', {row['credibility']}, {row['clarity_score']}, {row['extraction_confidence']}, '{row['intent']}', '{row['target']}', '{row['context']}', '{row['polarity']}', '{row['created_at']}', {row['decay_rate']}, {row['reinforcement_count']}, '{row['behavior_state']}')"
                values_list.append(val_str)
            
            insert_stmt = f"INSERT INTO behaviors (behavior_id, user_id, behavior_text, embedding, credibility, clarity_score, extraction_confidence, intent, target, context, polarity, created_at, decay_rate, reinforcement_count, behavior_state) VALUES\n"
            insert_stmt += ",\n".join(values_list) + ";\n\n"
            f.write(insert_stmt)
            
    print(f"Saved SQL INSERTs to {sql_path}")
    print("Ready for CBIE: INSERT INTO behaviors ...")

def main():
    print("=" * 60)
    print("CBIE Pilot Data Generator (Synthetic & Offline)")
    print("=" * 60)
    
    b_df, gt_df = generate_data()
    save_outputs(b_df, gt_df)

if __name__ == "__main__":
    main()
