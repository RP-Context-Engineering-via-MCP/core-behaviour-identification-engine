import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_KEY", "")
sb = create_client(url, key)

print("Fetching Core Behavior Profiles...")
response = sb.table("core_behavior_profiles").select("*").execute()

for p in response.data:
    print(f"\nUser: {p['user_id']}")
    print("-" * 40)
    print(f"Total raw behaviors: {p['total_raw_behaviors']}")
    interests = p.get('confirmed_interests', [])
    if isinstance(interests, str):
        try:
            interests = json.loads(interests)
        except:
            interests = []
    print(f"Confirmed interests: {len(interests)}")
    
    for i, inter in enumerate(interests):
        print(f"  {i+1}. Cluster ID: {inter.get('cluster_id')}")
        print(f"     Status: {inter.get('status')}")
        print(f"     Rep topics: {inter.get('representative_topics')}")
        print(f"     Core score: {inter.get('core_score')}")
        if 'consistency_score' in inter:
            print(f"     Consistency: {inter.get('consistency_score')}")
        if 'trend_score' in inter:
            print(f"     Trend: {inter.get('trend_score')}")

    print("\nIdentity Anchor Prompt:")
    print(p.get('identity_anchor_prompt', ''))
    print("=" * 60)
