import json
import random
import time
import uuid
import hashlib
from datetime import datetime, timedelta

# =================CONFIGURATION=================
# User profiles with different characteristics
USER_PROFILES = [
    {
        "user_id": "user_small_dataset",
        "num_behaviors": 8,
        "min_prompts": 5,
        "max_prompts": 12,
        "noise_ratio": 0.10,
        "days_back": 15,
        "description": "Small dataset - few behaviors, low activity"
    },
    {
        "user_id": "user_medium_clear",
        "num_behaviors": 12,
        "min_prompts": 15,
        "max_prompts": 35,
        "noise_ratio": 0.08,
        "days_back": 30,
        "description": "Medium dataset - clear patterns, low noise"
    },
    {
        "user_id": "user_large_diverse",
        "num_behaviors": 18,
        "min_prompts": 10,
        "max_prompts": 45,
        "noise_ratio": 0.20,
        "days_back": 60,
        "description": "Large dataset - diverse behaviors, higher noise"
    },
    {
        "user_id": "user_noisy_explorer",
        "num_behaviors": 10,
        "min_prompts": 8,
        "max_prompts": 20,
        "noise_ratio": 0.35,
        "days_back": 45,
        "description": "Exploratory user - many unrelated queries"
    },
    {
        "user_id": "user_focused_specialist",
        "num_behaviors": 5,
        "min_prompts": 30,
        "max_prompts": 80,
        "noise_ratio": 0.05,
        "days_back": 90,
        "description": "Focused specialist - few but very strong behaviors"
    }
]
# ===============================================

# --- DATA POOLS FOR REALISM ---
TOPICS = [
    "React hooks", "Next.js routing", "Vue composition API", "Angular signals",
    "TypeScript generics", "JavaScript promises", "Python decorators", "Django models",
    "Flask blueprints", "FastAPI", "PostgreSQL", "MongoDB aggregation", "Redis caching",
    "Docker containers", "Kubernetes pods", "AWS Lambda", "Google Cloud Run", "Azure Functions",
    "GraphQL", "REST APIs", "gRPC", "WebSockets", "CI/CD pipelines", "Git workflows",
    "TDD", "Integration testing", "End-to-end testing", "Code coverage", "Linting",
    "SQL injection", "XSS prevention", "CSRF protection", "JWT authentication", "OAuth2",
    "Encryption", "Hashing", "Salting", "SSL/TLS", "OWASP Top 10", "Microservices",
    "Monoliths", "Serverless", "Event-driven architecture", "CQRS", "Event sourcing",
    "Clean Architecture", "SOLID principles", "Design patterns", "System design",
    "Load balancing", "Caching strategies", "Database sharding", "Replication",
    "CAP theorem", "ACID properties", "BASE consistency", "Binary search", "Merge sort",
    "Quick sort", "Breadth-first search", "Depth-first search", "Dijkstra's algorithm",
    "Dynamic programming", "Greedy algorithms", "Backtracking", "Recursion", "Big O notation",
    "Hash tables", "Linked lists", "Trees", "Graphs", "Stacks", "Queues", "Heaps"
]

# Archetypes define the "Behavior" and the "Templates" used to generate prompts for it.
BEHAVIOR_ARCHETYPES = [
    {
        "text": "prefers visual diagrams and flowcharts",
        "category": "visual",
        "templates": [
            "Show me a diagram of {topic}", "Visual breakdown of {topic}", 
            "Can you create a diagram explaining {topic}?", "Draw a flowchart for {topic}", 
            "Illustrate {topic} visually", "I need a visual representation of {topic}"
        ]
    },
    {
        "text": "requests code examples and snippets",
        "category": "code",
        "templates": [
            "Show me code examples for {topic}", "I need code samples for {topic}",
            "Write a function to handle {topic}", "Can you provide sample code for {topic}?",
            "Give me a code snippet for {topic}", "Example implementation of {topic}",
            "Show me how to code {topic}", "Working code for {topic}"
        ]
    },
    {
        "text": "prefers step-by-step instructions",
        "category": "step",
        "templates": [
            "I need a step-by-step tutorial on {topic}", "Walk me through {topic}",
            "What are the steps involved in {topic}?", "Guide me through {topic} one step at a time",
            "How do I implement {topic}? Step by step", "Can you explain {topic} step-by-step?",
            "Sequential instructions for {topic}", "Show me the steps to set up {topic}"
        ]
    },
    {
        "text": "focuses on debugging and troubleshooting",
        "category": "debug",
        "templates": [
            "I'm getting an error with {topic}", "Help me debug {topic}",
            "Why isn't {topic} working?", "Troubleshoot {topic}",
            "Fix my {topic} problem", "What's wrong with my {topic}?",
            "How to fix {topic} errors", "Troubleshooting guide for {topic}"
        ]
    },
    {
        "text": "prefers concise, brief explanations",
        "category": "concise",
        "templates": [
            "Short explanation of {topic}", "TL;DR for {topic}",
            "Quick summary of {topic}", "In brief: {topic}",
            "Concise guide to {topic}", "Quick answer: {topic}",
            "Brief intro to {topic}", "Brief overview of {topic}"
        ]
    },
    {
        "text": "requests detailed, comprehensive explanations",
        "category": "deep",
        "templates": [
            "Detailed breakdown of {topic}", "Deep dive into {topic}",
            "Comprehensive guide to {topic}", "Explain {topic} in detail",
            "Everything about {topic}", "Thorough explanation of {topic}",
            "In-depth analysis of {topic}", "Full explanation of {topic}"
        ]
    },
    # Adding more specific behaviors to hit the >11 requirement easily
    {
        "text": "frequently asks about security vulnerabilities",
        "category": "security",
        "templates": [
            "How to prevent attacks on {topic}", "Security vulnerabilities in {topic}",
            "Is {topic} secure?", "Best security practices for {topic}",
            "Securing {topic}"
        ]
    },
    {
        "text": "focuses on performance optimization",
        "category": "perf",
        "templates": [
            "How to optimize {topic}", "Improving performance of {topic}",
            "Latency issues with {topic}", "Speed up {topic}",
            "Benchmarking {topic}"
        ]
    },
    {
        "text": "prefers theoretical concepts over implementation",
        "category": "theory",
        "templates": [
            "What is the theory behind {topic}?", "Concept of {topic}",
            "Define {topic}", "History of {topic}", "Why use {topic}?"
        ]
    },
    {
        "text": "asks for comparisons between technologies",
        "category": "compare",
        "templates": [
            "Compare {topic} vs alternatives", "{topic} vs others",
            "Pros and cons of {topic}", "When to use {topic}",
            "Difference between {topic} and..."
        ]
    },
    {
        "text": "requests best practices and standards",
        "category": "best_practice",
        "templates": [
            "Best practices for {topic}", "Industry standards for {topic}",
            "Clean way to do {topic}", "Proper convention for {topic}"
        ]
    }
]

NOISE_TEMPLATES = [
    "I need help with {topic}", "Tell me about {topic}", "{topic}", 
    "Info on {topic}", "Can you help with {topic}?", "What is {topic}?",
    "About {topic}", "{topic} please"
]

def generate_short_id(prefix=""):
    """Generates a short hex ID like 'prompt_09fba7'"""
    unique_str = f"{uuid.uuid4()}-{time.time()}"
    hash_str = hashlib.md5(unique_str.encode()).hexdigest()[:6]
    return f"{prefix}_{hash_str}"

def generate_dataset(user_id, num_behaviors, min_prompts, max_prompts, noise_ratio, start_time):
    prompts_list = []
    behaviors_list = []
    
    current_time = start_time.timestamp()
    
    # 1. Select Archetypes (ensure we have enough for the requested count)
    # If requested num_behaviors is higher than our unique archetypes, 
    # we recycle archetypes but treat them as distinct nuances for the script's sake.
    selected_archetypes = []
    while len(selected_archetypes) < num_behaviors:
        arch = random.choice(BEHAVIOR_ARCHETYPES)
        # Create a shallow copy so we can modify it slightly if needed, 
        # or just use it as a pattern source.
        selected_archetypes.append(arch)

    # 2. Generate Data per Behavior
    for i, arch in enumerate(selected_archetypes):
        
        # Decide how strong this behavior is
        count = random.randint(min_prompts, max_prompts)
        behavior_id = generate_short_id("beh")
        observation_id = generate_short_id("obs")
        
        # We need to track which prompt IDs belong to this behavior
        history_ids = []
        
        # Generate Prompts for this behavior
        session_base = f"sess_{arch['category']}_{i:03d}"
        
        for _ in range(count):
            prompt_id = generate_short_id("prompt")
            topic = random.choice(TOPICS)
            template = random.choice(arch['templates'])
            text = template.format(topic=topic)
            
            # Increment time slightly (between 2 mins and 3 hours)
            current_time += random.randint(120, 10800)
            
            p_obj = {
                "prompt_id": prompt_id,
                "prompt_text": text,
                "timestamp": int(current_time),
                "tokens": round(random.uniform(1.3, 13.0), 1),
                "is_noise": False,
                "user_id": user_id,
                "session_id": session_base
            }
            prompts_list.append(p_obj)
            history_ids.append(prompt_id)

        # Generate the Behavior Object
        # Calculate scores based on volume
        credibility = min(0.5 + (count * 0.015), 0.98) # Cap at 0.98
        confidence = min(0.5 + (count * 0.015), 0.96)
        
        b_obj = {
            "behavior_id": behavior_id,
            "observation_id": observation_id,
            "behavior_text": arch["text"],
            "credibility": round(credibility, 2),
            "reinforcement_count": count,
            "last_seen": int(current_time),
            "prompt_history_ids": history_ids, # THE CONNECTION
            "user_id": user_id,
            "session_id": session_base,
            "clarity_score": round(random.uniform(0.7, 0.99), 2),
            "confidence": round(confidence, 2)
        }
        behaviors_list.append(b_obj)

    # 3. Generate Noise (Prompts not linked to behaviors)
    total_prompts = len(prompts_list)
    noise_count = int(total_prompts * noise_ratio)
    
    # Reset time to intersperse noise, or just add them at random times?
    # Better: Insert them with random timestamps within the range we just covered.
    min_ts = prompts_list[0]['timestamp']
    max_ts = prompts_list[-1]['timestamp']
    
    for i in range(noise_count):
        prompt_id = generate_short_id("prompt")
        topic = random.choice(TOPICS)
        text = random.choice(NOISE_TEMPLATES).format(topic=topic)
        ts = random.randint(min_ts, max_ts)
        
        p_obj = {
            "prompt_id": prompt_id,
            "prompt_text": text,
            "timestamp": ts,
            "tokens": round(random.uniform(1.0, 6.0), 1),
            "is_noise": True,
            "user_id": user_id,
            "session_id": f"sess_noise_{i:03d}"
        }
        prompts_list.append(p_obj)

    # 4. Sort prompts by timestamp
    prompts_list.sort(key=lambda x: x['timestamp'])

    return behaviors_list, prompts_list

def generate_all_datasets():
    """Generate datasets for all user profiles"""
    all_datasets = {}
    
    print("="*70)
    print("GENERATING TEST DATASETS FOR MULTIPLE USERS")
    print("="*70)
    
    for profile in USER_PROFILES:
        user_id = profile["user_id"]
        print(f"\n📊 Generating dataset for: {user_id}")
        print(f"   Description: {profile['description']}")
        print(f"   Behaviors: {profile['num_behaviors']}, Prompts: {profile['min_prompts']}-{profile['max_prompts']}, Noise: {profile['noise_ratio']*100}%")
        
        start_time = datetime.now() - timedelta(days=profile["days_back"])
        
        behaviors, prompts = generate_dataset(
            user_id=user_id,
            num_behaviors=profile["num_behaviors"],
            min_prompts=profile["min_prompts"],
            max_prompts=profile["max_prompts"],
            noise_ratio=profile["noise_ratio"],
            start_time=start_time
        )
        
        all_datasets[user_id] = {
            "behaviors": behaviors,
            "prompts": prompts,
            "profile": profile
        }
        
        # Save individual user files
        behaviors_file = f"realistic_evaluation_set/behaviors_{user_id}.json"
        prompts_file = f"realistic_evaluation_set/prompts_{user_id}.json"
        
        with open(behaviors_file, "w") as f:
            json.dump(behaviors, f, indent=2)
        with open(prompts_file, "w") as f:
            json.dump(prompts, f, indent=2)
            
        print(f"   ✅ Generated {len(behaviors)} behaviors, {len(prompts)} prompts")
        print(f"   📁 Saved to: {behaviors_file}, {prompts_file}")
    
    # Generate summary file
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_users": len(USER_PROFILES),
        "users": {}
    }
    
    for user_id, data in all_datasets.items():
        summary["users"][user_id] = {
            "description": data["profile"]["description"],
            "behaviors_count": len(data["behaviors"]),
            "prompts_count": len(data["prompts"]),
            "noise_ratio": data["profile"]["noise_ratio"],
            "time_span_days": data["profile"]["days_back"],
            "files": {
                "behaviors": f"behaviors_{user_id}.json",
                "prompts": f"prompts_{user_id}.json"
            }
        }
    
    with open("realistic_evaluation_set/dataset_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "="*70)
    print("✅ ALL DATASETS GENERATED SUCCESSFULLY")
    print("="*70)
    print(f"\n📋 Summary saved to: realistic_evaluation_set/dataset_summary.json")
    print(f"\nGenerated {len(USER_PROFILES)} user datasets:")
    for user_id, info in summary["users"].items():
        print(f"  • {user_id}: {info['behaviors_count']} behaviors, {info['prompts_count']} prompts")
    print("\n")

if __name__ == "__main__":
    generate_all_datasets()