import json
import os
import numpy as np
import ast
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from logger import get_logger

log = get_logger(__name__)
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def _ms_epoch_to_iso(ms: Any) -> Optional[str]:
    """
    Convert a Unix-epoch millisecond bigint (from the BAC DB) to an ISO-8601
    string that the temporal analyser can sort and compare.
    Returns None if the value is missing or unparseable.
    """
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


class DataAdapter:
    """
    Manages all database I/O for the CBIE engine.

    Two separate Supabase connections are maintained:
      - self.bac_supabase  — READ-ONLY connection to the BAC (Behaviour Analysis
                             Component) database where the raw behavior events live.
      - self.supabase      — READ/WRITE connection to the CBIE database where
                             core_behavior_profiles are stored.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.output_dir = os.path.join(self.data_dir, "profiles")
        os.makedirs(self.output_dir, exist_ok=True)

        # ── CBIE DB (write core_behavior_profiles) ────────────────────────
        url: str = os.environ.get("SUPABASE_URL", "")
        key: str = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            log.warning(
                "Missing SUPABASE_URL/KEY — profile saving will fail",
                extra={"stage": "INIT"},
            )
            self.supabase: Optional[Client] = None
        else:
            self.supabase: Optional[Client] = create_client(url, key)
            log.info("CBIE Supabase client initialised", extra={"stage": "INIT", "url": url})

        # ── BAC DB (read behaviors only) ──────────────────────────────────
        bac_url: str = os.environ.get("BAC_SUPABASE_URL", "")
        bac_key: str = os.environ.get("BAC_SUPABASE_KEY", "")
        if not bac_url or not bac_key:
            log.warning(
                "Missing BAC_SUPABASE_URL/KEY — falling back to CBIE DB for behavior reads",
                extra={"stage": "INIT"},
            )
            # Graceful fallback: use the same client so the old test data still works
            self.bac_supabase: Optional[Client] = self.supabase
            self._bac_timestamps_are_bigint = False
        else:
            self.bac_supabase: Optional[Client] = create_client(bac_url, bac_key)
            self._bac_timestamps_are_bigint = True   # BAC DB stores created_at as bigint ms
            log.info("BAC Supabase client initialised", extra={"stage": "INIT", "url": bac_url})

    # ─────────────────────────────────────────────────────────────────────────
    # Checkpoint helpers (CBIE DB)
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_last_processed_timestamp(self, user_id: str) -> Optional[str]:
        """
        Returns the last_processed_timestamp for the user's profile, or None if no
        profile exists yet.  Used by the pipeline for incremental-run decisions.
        """
        if not self.supabase:
            return None
        try:
            response = (
                self.supabase.table("core_behavior_profiles")
                .select("last_processed_timestamp")
                .eq("user_id", user_id)
                .execute()
            )
            if response.data:
                return response.data[0].get("last_processed_timestamp")
        except Exception as e:
            log.warning(
                "Could not fetch last_processed_timestamp",
                extra={"user_id": user_id, "error": str(e)},
            )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Behavior fetch (BAC DB)
    # ─────────────────────────────────────────────────────────────────────────

    def fetch_user_history(
        self, user_id: str, limit: int = 500, since_timestamp: str = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves ACTIVE behavior records for a user from the BAC database.

        The BAC schema stores timestamps as Unix-epoch milliseconds (bigint).
        This method converts them to ISO-8601 strings so the temporal analyser
        can work with them transparently.

        since_timestamp: ISO-8601 string (from the CBIE checkpoint).
                         Converted to epoch-ms for the BAC bigint comparison.
        """
        if not self.bac_supabase:
            log.error(
                "BAC Supabase client not initialized",
                extra={"user_id": user_id, "stage": "FETCH"},
            )
            return []

        # Convert ISO checkpoint → epoch-ms if the BAC stores timestamps as bigint
        since_epoch_ms: Optional[int] = None
        if since_timestamp and self._bac_timestamps_are_bigint:
            try:
                dt = datetime.fromisoformat(since_timestamp.replace("Z", "+00:00"))
                since_epoch_ms = int(dt.timestamp() * 1000)
            except Exception:
                since_epoch_ms = None

        log.info(
            "Querying BAC behaviors table",
            extra={
                "user_id": user_id,
                "stage": "FETCH",
                "filter": "behavior_state=ACTIVE",
                "limit": limit,
                "since_ms": since_epoch_ms,
            },
        )

        try:
            query = (
                self.bac_supabase.table("behaviors")
                .select("*")
                .eq("user_id", user_id)
                .eq("behavior_state", "ACTIVE")
            )
            if since_epoch_ms is not None:
                query = query.gt("created_at", since_epoch_ms)
            elif since_timestamp and not self._bac_timestamps_are_bigint:
                # Fallback path — old CBIE test DB with TIMESTAMPTZ
                query = query.gt("created_at", since_timestamp)

            response = query.order("created_at", desc=True).limit(limit).execute()
        except Exception as e:
            log.error(
                "Error querying BAC behaviors table",
                extra={"user_id": user_id, "stage": "FETCH", "error": str(e)},
            )
            return []

        records = response.data
        if not records:
            log.warning(
                "No ACTIVE behavior records found in BAC DB",
                extra={"user_id": user_id, "stage": "FETCH"},
            )
            return []

        user_logs = []
        for record in records:
            # Convert bigint epoch-ms → ISO string; fall back if already a string
            raw_ts = record.get("created_at")
            if self._bac_timestamps_are_bigint:
                iso_ts = _ms_epoch_to_iso(raw_ts)
            else:
                iso_ts = raw_ts  # already a TIMESTAMPTZ string

            entry = {
                "event_id": record.get("behavior_id", f"beh_{np.random.randint(1000)}"),
                "user_id": record.get("user_id", user_id),
                "timestamp": iso_ts,
                "source_text": record.get("behavior_text", ""),
                "intent": record.get("intent", ""),
                "target": record.get("target", ""),
                "context": record.get("context", "general"),
                "polarity": record.get("polarity", ""),
                "scores": {
                    "credibility": float(record.get("credibility") or 0.5),
                    "clarity_score": float(record.get("clarity_score") or 0.5),
                    "extraction_confidence": float(record.get("extraction_confidence") or 0.5),
                },
            }

            # Parse the vector embedding
            embedding_data = record.get("embedding")
            if embedding_data is not None:
                if isinstance(embedding_data, str) and embedding_data.startswith("["):
                    try:
                        entry["text_embedding"] = np.array(
                            ast.literal_eval(embedding_data), dtype=np.float32
                        )
                    except Exception as e:
                        log.warning(
                            "Could not parse string embedding",
                            extra={"event_id": entry.get("event_id"), "error": str(e), "stage": "FETCH"},
                        )
                        entry["text_embedding"] = None
                elif isinstance(embedding_data, list):
                    entry["text_embedding"] = np.array(embedding_data, dtype=np.float32)
                else:
                    entry["text_embedding"] = None
            else:
                entry["text_embedding"] = None

            user_logs.append(entry)

        # Sort chronologically (temporal analyser expects oldest first)
        user_logs.sort(key=lambda x: str(x.get("timestamp", "")))
        log.info(
            "Behavior fetch complete",
            extra={"user_id": user_id, "stage": "FETCH", "records_loaded": len(user_logs)},
        )
        return user_logs

    # ─────────────────────────────────────────────────────────────────────────
    # Profile save (CBIE DB)
    # ─────────────────────────────────────────────────────────────────────────

    def save_profile(self, user_id: str, profile: Dict[str, Any]) -> str:
        """
        Persists the finalised Core Behaviour Profile to local storage AND to the
        CBIE Supabase database (core_behavior_profiles table).
        """
        # 1. Local JSON file
        file_path = os.path.join(self.output_dir, f"{user_id}_profile.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4)
        log.info("Profile saved locally", extra={"user_id": user_id, "stage": "SAVE", "path": file_path})

        # 2. CBIE Supabase upsert
        if self.supabase:
            try:
                db_record = {
                    "user_id": user_id,
                    "total_raw_behaviors": profile.get("total_raw_behaviors", 0),
                    "confirmed_interests": json.dumps(profile.get("confirmed_interests", [])),
                    "updated_at": "now()",
                    "last_processed_timestamp": "now()",
                }
                self.supabase.table("core_behavior_profiles").upsert(
                    db_record, on_conflict="user_id"
                ).execute()
                log.info(
                    "Profile upserted to CBIE core_behavior_profiles",
                    extra={"user_id": user_id, "stage": "SAVE"},
                )
            except Exception as e:
                log.error(
                    "Could not save profile to CBIE Supabase",
                    extra={"user_id": user_id, "stage": "SAVE", "error": str(e)},
                )

        return file_path
