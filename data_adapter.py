import json
import os
import numpy as np
import ast
from typing import List, Dict, Any

from logger import get_logger

log = get_logger(__name__)
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class DataAdapter:
    """
    Simulates fetching behavioral logs from a hybrid database and saving the final
    Core Behaviour Profile. In a real scenario, this would connect to MongoDB/SQL.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_dir = os.path.join(self.data_dir, "profiles")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize Supabase Client
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            log.warning("Missing Supabase credentials in .env — DB connection will fail", extra={"stage": "INIT"})
            self.supabase: Client = None
        else:
            self.supabase: Client = create_client(url, key)

    def fetch_user_history(self, user_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retrieves the time-series objects of behaviors for a given user directly from Supabase.
        Uses a sliding window (limit) to prevent OOM errors on massive datasets, fetching
        the most recent behaviors.
        """
        if not self.supabase:
            log.error("Supabase client not initialized — cannot fetch data", extra={"user_id": user_id, "stage": "FETCH"})
            return []
            
        log.info("Querying Supabase behaviors table", extra={"user_id": user_id, "stage": "FETCH", "filter": "behavior_state=ACTIVE", "limit": limit})
        try:
            response = self.supabase.table('behaviors').select('*').eq('user_id', user_id).eq('behavior_state', 'ACTIVE').order('created_at', desc=True).limit(limit).execute()
        except Exception as e:
            log.error("Error querying Supabase", extra={"user_id": user_id, "stage": "FETCH", "error": str(e)})
            return []
            
        records = response.data
        if not records:
            log.warning("No ACTIVE behavior records found in Supabase", extra={"user_id": user_id, "stage": "FETCH"})
            return []
             
        user_logs = []
        for record in records:
            # Map specific Supabase schema fields to the internal representations needed
            # Fallback to defaults to prevent crashes if schema is slightly off
            entry = {
                "event_id": record.get("behavior_id", f"beh_{np.random.randint(1000)}"),
                "user_id": record.get("user_id", user_id),
                "timestamp": record.get("created_at"), 
                "source_text": record.get("behavior_text", ""),
                "intent": record.get("intent", ""),
                "target": record.get("target", ""),
                "context": record.get("context", "general"),
                "polarity": record.get("polarity", ""),
                "scores": {
                    "credibility": float(record.get("credibility", 0.5)),
                    "clarity_score": float(record.get("clarity_score", 0.5)),
                    "extraction_confidence": float(record.get("extraction_confidence", 0.5))
                }
            }
            
            # Attempt to safely parse the embeddings
            # Depending on how the DB stores embeddings (vector type vs jsonb), it might come back as a string or list
            embedding_data = record.get("embedding")
            if embedding_data is not None:
                if isinstance(embedding_data, str) and embedding_data.startswith("["):
                    try:
                        emb_list = ast.literal_eval(embedding_data)
                        entry["text_embedding"] = np.array(emb_list, dtype=np.float32)
                    except Exception as e:
                        log.warning("Could not parse string embedding", extra={"event_id": entry.get("event_id"), "error": str(e), "stage": "FETCH"})
                        entry["text_embedding"] = None
                elif isinstance(embedding_data, list):
                    # Native JSON parsed array
                     entry["text_embedding"] = np.array(embedding_data, dtype=np.float32)
                else:
                    entry["text_embedding"] = None
            else:
                 entry["text_embedding"] = None
                
            user_logs.append(entry)
            
        # Ensure logs are sorted by time 
        user_logs.sort(key=lambda x: str(x.get('timestamp', '')))
        log.info("Behavior fetch complete", extra={"user_id": user_id, "stage": "FETCH", "records_loaded": len(user_logs)})
        return user_logs

    def save_profile(self, user_id: str, profile: Dict[str, Any]) -> str:
        """
        Persists the finalized Core Behaviour Profile to local storage AND to Supabase.
        """
        # 1. Save locally
        file_path = os.path.join(self.output_dir, f"{user_id}_profile.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=4)
        log.info("Profile saved locally", extra={"user_id": user_id, "stage": "SAVE", "path": file_path})
        
        # 2. Save to Supabase
        if self.supabase:
            try:
                db_record = {
                    "user_id": user_id,
                    "total_raw_behaviors": profile.get("total_raw_behaviors", 0),
                    "confirmed_interests": json.dumps(profile.get("confirmed_interests", [])),
                    "updated_at": "now()"
                }
                self.supabase.table("core_behavior_profiles").upsert(
                    db_record, on_conflict="user_id"
                ).execute()
                log.info("Profile upserted to Supabase core_behavior_profiles", extra={"user_id": user_id, "stage": "SAVE"})
            except Exception as e:
                log.error("Could not save profile to Supabase", extra={"user_id": user_id, "stage": "SAVE", "error": str(e)})
        
        return file_path
