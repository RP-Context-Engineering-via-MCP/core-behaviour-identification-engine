import csv
import random
import uuid
import time
from datetime import datetime, timedelta

def generate_behavior_data():
    users = {
        "test_user_health": {
            "scenarios": [
                {"label": "Stable Fact: Peanut Allergy", "theme": "severe peanut allergy", "count": 4, "polarity": "NEGATIVE", "intent": "CONSTRAINT", "cred": (0.9, 0.95), "clarity": (0.9, 0.95), "spread": 90, "indicators": ["avoids", "dislikes", "rejects", "steers clear of"]},
                {"label": "Stable Fact: Lactose Intolerance", "theme": "lactose-containing products", "count": 3, "polarity": "NEGATIVE", "intent": "CONSTRAINT", "cred": (0.9, 0.95), "clarity": (0.9, 0.95), "spread": 90, "indicators": ["avoids", "dislikes", "rejects"]},
                {"label": "Stable: Plant-based Cooking", "theme": "plant-based protein sources and vegan recipes", "count": 18, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.85, 0.92), "clarity": (0.8, 0.88), "spread": 90, "indicators": ["prefers", "likes", "enjoys", "favors", "tends to choose"]},
                {"label": "Stable: Yoga", "theme": "practicing morning yoga and meditation", "count": 15, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.8, 0.9), "clarity": (0.8, 0.85), "spread": 90, "indicators": ["enjoys", "has a habit of", "frequently chooses", "often engages in"]},
                {"label": "Emerging: Marathon Running", "theme": "marathon training programs and endurance running", "count": 8, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity": (0.7, 0.78), "spread": 21, "indicators": ["is inclined toward", "frequently chooses", "often engages in"]},
                {"label": "Noise: Random Trivia", "theme": "random history trivia and science facts", "count": 6, "polarity": "NEUTRAL", "intent": "QUERY", "cred": (0.3, 0.4), "clarity": (0.3, 0.45), "spread": 90, "indicators": ["is curious about", "asks about", "searches for"]},
                {"label": "Stable: Organic Grocery", "theme": "organic vegetables and sustainable grocery shopping", "count": 14, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.82, 0.88), "clarity": (0.8, 0.88), "spread": 90, "indicators": ["usually selects", "prefers", "likes", "favors"]},
                {"label": "Contradicted: Peanut Butter", "theme": "creamy peanut butter recipes", "count": 4, "polarity": "NEGATIVE", "intent": "PREFERENCE", "cred": (0.5, 0.6), "clarity": (0.5, 0.65), "spread": 60, "indicators": ["is inclined toward", "tends to choose"]},
                {"label": "Emerging: Herbal Tea", "theme": "herbal tea varieties and brewing methods", "count": 4, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity": (0.7, 0.75), "spread": 14, "indicators": ["enjoys", "prefers"]}
            ],
            "total_noise": 5
        },
        "test_user_finance": {
            "scenarios": [
                {"label": "Stable Fact: Risk Aversion", "theme": "high-risk speculative investments", "count": 3, "polarity": "NEGATIVE", "intent": "CONSTRAINT", "cred": (0.9, 0.95), "clarity": (0.9, 0.95), "spread": 90, "indicators": ["avoids", "steers clear of", "rejects"]},
                {"label": "Stable: Dividend Stocks", "theme": "dividend-paying blue chip stocks for stable income", "count": 20, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.85, 0.92), "clarity": (0.8, 0.88), "spread": 90, "indicators": ["prefers", "usually selects", "tends to choose", "favors"]},
                {"label": "Stable: Real Estate", "theme": "real estate investment trusts and property market trends", "count": 16, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.8, 0.9), "clarity": (0.8, 0.85), "spread": 90, "indicators": ["enjoys", "has a habit of", "frequently chooses", "often engages in"]},
                {"label": "Emerging: Crypto", "theme": "cryptocurrency market analysis and blockchain assets", "count": 9, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity": (0.7, 0.78), "spread": 21, "indicators": ["is inclined toward", "frequently chooses", "often engages in"]},
                {"label": "Archived: Bonds", "theme": "traditional government bond trading", "count": 5, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.1, 0.2), "clarity": (0.2, 0.3), "spread": 30, "end_offset": 60, "indicators": ["previously liked", "used to select", "formerly engaged in"]},
                {"label": "Stable: Tax Optimization", "theme": "tax-efficient investing and optimization strategies", "count": 12, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.8, 0.88), "clarity": (0.8, 0.85), "spread": 90, "indicators": ["prefers", "likes", "favors", "tends to choose"]},
                {"label": "Emerging: ESG", "theme": "ESG and sustainable investing principles", "count": 5, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity": (0.7, 0.75), "spread": 14, "indicators": ["enjoys", "prefers"]},
                {"label": "Noise Filter: Meme Stocks", "theme": "meme stock jokes and social media stock hype", "count": 3, "polarity": "NEUTRAL", "intent": "QUERY", "cred": (0.2, 0.35), "clarity": (0.3, 0.45), "spread": 90, "indicators": ["is curious about", "asks about"]}
            ],
            "total_noise": 5
        },
        "test_user_tech": {
            "scenarios": [
                {"label": "Stable Fact: Celiac Disease", "theme": "gluten-containing foods and wheat products", "count": 3, "polarity": "NEGATIVE", "intent": "CONSTRAINT", "cred": (0.9, 0.95), "clarity": (0.9, 0.95), "spread": 90, "indicators": ["avoids", "rejects", "steers clear of"]},
                {"label": "Stable: Python Backend", "theme": "Python backend development and FastAPI frameworks", "count": 18, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.85, 0.92), "clarity": (0.8, 0.88), "spread": 90, "indicators": ["prefers", "likes", "enjoys", "favors", "tends to choose"]},
                {"label": "Stable: Cloud Infra", "theme": "AWS cloud infrastructure and Docker containerization", "count": 14, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.8, 0.9), "clarity": (0.8, 0.85), "spread": 90, "indicators": ["enjoys", "has a habit of", "frequently chooses", "often engages in"]},
                {"label": "Emerging: AI/ML", "theme": "machine learning algorithms and AI research papers", "count": 9, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity_start": 0.65, "clarity_end": 0.92, "spread": 21, "indicators": ["is inclined toward", "frequently chooses", "often engages in"]},
                {"label": "Stable: PostgreSQL", "theme": "PostgreSQL database administration and query optimization", "count": 12, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.8, 0.88), "clarity": (0.8, 0.85), "spread": 90, "indicators": ["prefers", "likes", "favors", "tends to choose"]},
                {"label": "Emerging: Rust", "theme": "Rust systems programming and memory safety", "count": 5, "polarity": "POSITIVE", "intent": "PREFERENCE", "cred": (0.7, 0.75), "clarity": (0.7, 0.75), "spread": 14, "indicators": ["enjoys", "prefers"]},
                {"label": "Polarity Separation: Legacy PHP", "theme": "working with legacy PHP codebases", "count": 5, "polarity": "NEGATIVE", "intent": "PREFERENCE", "cred": (0.7, 0.8), "clarity": (0.7, 0.8), "spread": 60, "indicators": ["dislikes", "avoids", "rejects"]}
            ],
            "total_noise": 4
        }
    }

    now = datetime.now()
    all_rows = []

    for user_id, user_config in users.items():
        user_rows = []
        for scenario in user_config["scenarios"]:
            count = scenario["count"]
            spread = scenario["spread"]
            end_offset = scenario.get("end_offset", 0)
            
            # Base end time for the scenario
            end_time = now - timedelta(days=end_offset)
            start_time = end_time - timedelta(days=spread)
            
            for i in range(count):
                # Generate a roughly even spread with some randomness
                day_offset = (spread / count) * i + random.uniform(-0.5, 0.5)
                timestamp_dt = start_time + timedelta(days=max(0, day_offset))
                timestamp_ms = int(timestamp_dt.timestamp() * 1000)
                
                indicator = random.choice(scenario["indicators"])
                behavior_text = f"{indicator} {scenario['theme']}"
                
                cred = random.uniform(*scenario["cred"])
                
                # Handle increasing clarity for trend test
                if "clarity_start" in scenario:
                    progress = i / (count - 1) if count > 1 else 0
                    clarity = scenario["clarity_start"] + progress * (scenario["clarity_end"] - scenario["clarity_start"])
                else:
                    clarity = random.uniform(*scenario["clarity"])
                
                row = {
                    "behavior_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "session_id": str(uuid.uuid4()),
                    "behavior_text": behavior_text,
                    "credibility": round(cred, 4),
                    "extraction_confidence": round(cred, 4),
                    "clarity_score": round(clarity, 4),
                    "linguistic_strength": 0.5,
                    "decay_rate": 0.015,
                    "reinforcement_count": 1,
                    "created_at": timestamp_ms,
                    "last_seen_at": timestamp_ms,
                    "prompt_history_ids": "[]",
                    "behavior_state": "ACTIVE",
                    "superseded_by_id": "",
                    "related_behaviors": "[]",
                    "last_decay_applied_at": timestamp_ms,
                    "context_notes": scenario["label"],
                    "intent": scenario["intent"],
                    "target": scenario["theme"].split()[0],
                    "context": "lifestyle" if "health" in user_id else "finance" if "finance" in user_id else "tech",
                    "polarity": scenario["polarity"],
                    "last_accessed_at": timestamp_ms,
                    "search_vector": "",
                    "embedding": "",
                    "canonical_embedding": ""
                }
                user_rows.append(row)
        
        # Add random noise
        for _ in range(user_config["total_noise"]):
            timestamp_dt = now - timedelta(days=random.randint(0, 90))
            timestamp_ms = int(timestamp_dt.timestamp() * 1000)
            row = {
                "behavior_id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": str(uuid.uuid4()),
                "behavior_text": f"random query about {random.choice(['weather', 'time', 'news', 'sports', 'movies'])}",
                "credibility": round(random.uniform(0.2, 0.4), 4),
                "extraction_confidence": 0.5,
                "clarity_score": round(random.uniform(0.3, 0.5), 4),
                "linguistic_strength": 0.5,
                "decay_rate": 0.015,
                "reinforcement_count": 1,
                "created_at": timestamp_ms,
                "last_seen_at": timestamp_ms,
                "prompt_history_ids": "[]",
                "behavior_state": "ACTIVE",
                "superseded_by_id": "",
                "related_behaviors": "[]",
                "last_decay_applied_at": timestamp_ms,
                "context_notes": "Noise: DBSCAN drop",
                "intent": "QUERY",
                "target": "noise",
                "context": "general",
                "polarity": "NEUTRAL",
                "last_accessed_at": timestamp_ms,
                "search_vector": "",
                "embedding": "",
                "canonical_embedding": ""
            }
            user_rows.append(row)
            
        all_rows.extend(user_rows)
        
        # Save individual user file
        filename = f"d:\\Academics\\impl-final\\cbie_engine\\data\\{user_id}_behaviors.csv"
        write_csv(filename, user_rows)
        print(f"Generated {len(user_rows)} behaviors for {user_id} -> {filename}")

    # Save combined file
    combined_filename = "d:\\Academics\\impl-final\\cbie_engine\\data\\test_all_users_behaviors.csv"
    write_csv(combined_filename, all_rows)
    print(f"Generated {len(all_rows)} total behaviors -> {combined_filename}")

def write_csv(filename, rows):
    if not rows: return
    keys = rows[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(rows)

if __name__ == "__main__":
    generate_behavior_data()
