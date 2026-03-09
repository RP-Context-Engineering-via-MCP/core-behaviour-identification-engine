import argparse
import numpy as np
from typing import Dict, Any, List, Callable, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.manifold import TSNE
import os

from logger import get_logger
from data_adapter import DataAdapter
from topic_discovery import TopicDiscoverer
from temporal_analysis import TemporalAnalyzer
from confirmation_model import ConfirmationModel

log = get_logger(__name__)

class CBIEPipeline:
    """
    The orchestrator for the Core Behaviour Identification Engine.
    Executes the ingestion, analysis (NLP, Temporal, Confirmation), and output phases.
    """
    
    def __init__(self):
        self.data_adapter = DataAdapter()
        self.topic_discoverer = TopicDiscoverer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.confirmation_model = ConfirmationModel()

    def generate_identity_prompt(self, profile: Dict[str, Any]) -> str:
        """
        Creates a rigid System Prompt string anchored to the user's Core Behaviour Profile.
        """
        user_id = profile.get("user_id", "Unknown")
        interests = profile.get("confirmed_interests", [])
        
        facts = [i for i in interests if i.get("status") == "Stable Fact"]
        stable = [i for i in interests if i.get("status") == "Stable"]
        emerging = [i for i in interests if i.get("status") == "Emerging"]
        archived = [i for i in interests if i.get("status") == "ARCHIVED_CORE"]
        
        # Extract topics
        def get_topics(items):
            res = []
            for item in items:
                topics = item.get("representative_topics", [])
                if topics:
                    res.append(topics[0])
            return res
            
        fact_topics = get_topics(facts)
        stable_topics = get_topics(stable)
        emerging_topics = get_topics(emerging)
        archived_topics = get_topics(archived)
        
        prompt_parts = [f"--- SYSTEM IDENTITY ANCHOR FOR USER: {user_id} ---"]
        prompt_parts.append("You are speaking with a user who has following core traits and constraints.")
        
        if fact_topics:
            prompt_parts.append(f"\nCRITICAL CONSTRAINTS (Never violate):")
            for f in fact_topics:
                prompt_parts.append(f"- {f}")
                
        if stable_topics:
            prompt_parts.append(f"\nVERIFIED STABLE PREFERENCES:")
            for s in stable_topics:
                prompt_parts.append(f"- {s}")
                
        if emerging_topics:
            prompt_parts.append(f"\nEMERGING INTERESTS (Needs more verification):")
            for e in emerging_topics:
                prompt_parts.append(f"- {e}")
                
        if archived_topics:
            prompt_parts.append(f"\nARCHIVED OUTDATED HABITS (Do not use as active context):")
            for a in archived_topics:
                prompt_parts.append(f"- {a}")
                
        return "\n".join(prompt_parts)

    def process_user(self, user_id: str, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Dict[str, Any]:
        """
        Runs the full CBIE pipeline for a single user.
        progress_callback(stage, processed, total) is called at key stages.
        """
        log.info("Starting CBIE Pipeline", extra={"user_id": user_id, "stage": "START"})
        
        # 1. Ingestion
        log.info("Fetching user history from Supabase", extra={"user_id": user_id, "stage": "INGESTION"})
        behaviors = self.data_adapter.fetch_user_history(user_id)
        if not behaviors:
            log.warning("No behaviors found for user — aborting pipeline", extra={"user_id": user_id, "stage": "INGESTION"})
            return {}

        total_behaviors = len(behaviors)
        if progress_callback:
            progress_callback("INGESTION_COMPLETE", total_behaviors, total_behaviors)
            
        # 2. Topic Discovery & Fact Isolation (Stage 1)
        log.info("Running Topic Discovery, Fact Extraction, and Clustering", extra={"user_id": user_id, "stage": "TOPIC_DISCOVERY", "total_behaviors": total_behaviors})
        fact_behaviors, standard_behaviors, _, labels = self.topic_discoverer.process_behaviors(
            behaviors, progress_callback=progress_callback
        )
        
        # 3. Temporal Analysis & Confirmation (Stage 2 & 3)
        confirmed_interests = []
        
        # --- Handle Absolute Facts first ---
        # Pre-compute embeddings of all fact source texts for contradiction detection later
        fact_texts = []
        fact_embeddings = np.array([])
        if fact_behaviors:
            log.info("Absolute facts identified", extra={"user_id": user_id, "stage": "FACT_ISOLATION", "fact_count": len(fact_behaviors)})
            all_fact_topics = [fb.get('explicit_topics', [fb.get('source_text')])[0] for fb in fact_behaviors]
            fact_texts = [fb.get('source_text', '') for fb in fact_behaviors if fb.get('source_text')]
            if fact_texts:
                fact_embeddings = self.topic_discoverer.generate_embeddings(fact_texts)
            
            interest_profile = {
                "cluster_id": "absolute_fact",
                "representative_topics": all_fact_topics,
                "frequency": len(fact_behaviors),
                "consistency_score": 0.0,
                "trend_score": 0.0,
                "core_score": 1.0,
                "status": self.confirmation_model.determine_status(1.0, is_fact=True)
            }
            confirmed_interests.append(interest_profile)
        
        # --- Handle Standard Clusters ---
        # Group behaviors by cluster
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for b in standard_behaviors:
            c_id = b.get('cluster_id')
            if c_id == -1: continue # Skip noise
            if c_id not in clusters:
                clusters[c_id] = []
            clusters[c_id].append(b)
            
        log.info("HDBSCAN clustering complete", extra={"user_id": user_id, "stage": "CLUSTERING", "cluster_count": len(clusters)})
        if progress_callback:
            progress_callback("CLUSTERING_COMPLETE", len(clusters), len(clusters))
        
        # 3. Temporal Analysis & Confirmation (Stage 2 & 3)
        log.info("Analyzing temporal consistency and confirming core interests", extra={"user_id": user_id, "stage": "TEMPORAL_ANALYSIS"})

        max_freq = max([len(c) for c in clusters.values()]) if clusters else 0
        num_clusters = len(clusters)

        for cluster_idx, (cluster_id, cluster_behaviors) in enumerate(clusters.items()):
            if progress_callback:
                progress_callback("TEMPORAL_ANALYSIS", cluster_idx + 1, num_clusters)
            freq = len(cluster_behaviors)
            
            # Extract timestamps and scores
            timestamps = [b.get('timestamp') for b in cluster_behaviors if b.get('timestamp')]
            scores = [b.get('scores', {}).get('clarity_score', 0.5) for b in cluster_behaviors]
            
            # Compute average credibility for the cluster
            avg_credibility = sum(scores_obj.get('credibility', 0.5) for scores_obj in [b.get('scores', {}) for b in cluster_behaviors]) / freq
            
            # Temporal Analysis
            consistency = self.temporal_analyzer.calculate_consistency(timestamps)
            trend = self.temporal_analyzer.calculate_trend(scores)
            
            # Confirmation
            core_score = self.confirmation_model.calculate_core_score(consistency, trend, freq, max_freq, avg_credibility)
            status = self.confirmation_model.determine_status(core_score, is_fact=False)
            
            # Generate a cohesive label using Azure OpenAI
            raw_cluster_texts = [b.get('source_text', '') for b in cluster_behaviors if b.get('source_text')]
            generalized_label = self.topic_discoverer.generalize_cluster_topic(raw_cluster_texts)
            representative_topics = [generalized_label]
            
            # --- FIX 2: Semantic Contradiction Suppression ---
            # If this cluster is semantically OPPOSED to a confirmed Stable Fact, mark it
            # as CONTRADICTED and exclude it. This prevents adversarial/opposite behaviors
            # (e.g., "Steak" for a vegan user) from being confirmed as stable interests.
            if status != "Noise" and len(fact_embeddings) > 0 and raw_cluster_texts:
                cluster_embedding = self.topic_discoverer.generate_embeddings(raw_cluster_texts[:5])  # sample
                cluster_mean = cluster_embedding.mean(axis=0, keepdims=True)
                fact_mean = fact_embeddings.mean(axis=0, keepdims=True)
                sim = cosine_similarity(cluster_mean, fact_mean)[0][0]
                
                # Check polarity of behaviors in this cluster
                cluster_polarities = [str(b.get('polarity', '') or '').upper() for b in cluster_behaviors]
                has_negative_polarity = cluster_polarities.count('NEGATIVE') > len(cluster_polarities) / 2
                
                # A cluster contradicts facts if:
                #   (a) it is semantically distant from facts (sim < 0.1) AND has NEGATIVE polarity, OR
                #   (b) it is semantically very far AND is predominantly opposite sentiment
                CONTRADICTION_SIM_THRESHOLD = 0.1
                if sim < CONTRADICTION_SIM_THRESHOLD and has_negative_polarity:
                    log.info(
                        "Cluster suppressed — contradicts confirmed facts",
                        extra={"stage": "CONTRADICTION_CHECK", "cluster_id": cluster_id,
                               "similarity": round(float(sim), 4), "label": generalized_label}
                    )
                    status = "CONTRADICTED"
            
            # --- FIX 3: Classifier & Complexity Noise Filter ---
            # Random trivia (high classifier trivia score, low complexity) clusters nicely but shouldn't form "Core Interests"
            if status not in ("Noise", "CONTRADICTED"):
                # Use clarity_score as a proxy for complexity/specificity if extraction_confidence isn't ideal
                complexities = [b.get('scores', {}).get('clarity_score', 0.5) for b in cluster_behaviors]
                avg_complexity = sum(complexities) / len(complexities) if complexities else 0.5
                
                # Check the new classifier trivia score
                trivia_scores = [b.get('scores', {}).get('classifier_trivia', 0.0) for b in cluster_behaviors]
                avg_trivia_score = sum(trivia_scores) / len(trivia_scores) if trivia_scores else 0.0
                
                log.info(
                    "Cluster stats for calibration",
                    extra={"stage": "NOISE_CALIBRATION", "cluster_id": cluster_id,
                           "avg_trivia_score": round(avg_trivia_score, 3), 
                           "avg_complexity": round(avg_complexity, 3), 
                           "label": generalized_label}
                )
                
                if avg_trivia_score > 0.8 and avg_complexity < 0.65:
                     log.info(
                         "Cluster suppressed — excessive low-complexity noise",
                         extra={"stage": "NOISE_FILTER", "cluster_id": cluster_id,
                                "avg_trivia_score": round(avg_trivia_score, 3), 
                                "avg_complexity": round(avg_complexity, 3), 
                                "label": generalized_label}
                     )
                     status = "Noise"
                
            interest_profile = {
                "cluster_id": cluster_id,
                "representative_topics": representative_topics,
                "frequency": freq,
                "consistency_score": consistency,
                "trend_score": trend,
                "core_score": core_score,
                "avg_credibility": round(avg_credibility, 3),
                "status": status
            }
            
            if status not in ("Noise", "CONTRADICTED"):
                confirmed_interests.append(interest_profile)
                 
        log.info("Confirmation model complete", extra={"user_id": user_id, "stage": "CONFIRMATION", "confirmed_count": len(confirmed_interests)})
        if progress_callback:
            progress_callback("BUILDING_PROFILE", 1, 1)

        # 4a. Build Embedding Map via t-SNE
        # Collect all standard behaviors that have a valid embedding + their cluster labels
        embedding_map = []
        try:
            embeddable = [
                b for b in standard_behaviors
                if b.get("text_embedding") is not None and len(b["text_embedding"]) > 0
            ]
            if len(embeddable) >= 4:  # t-SNE needs at least 4 points
                vectors = np.array([b["text_embedding"] for b in embeddable])
                # perplexity must be < n_samples; cap at 30
                perp = min(30, len(embeddable) - 1)
                tsne = TSNE(n_components=2, perplexity=perp, random_state=42, n_iter=300)
                coords = tsne.fit_transform(vectors)

                # Map cluster_id -> label/status from confirmed_interests
                cluster_meta: Dict[Any, Dict] = {}
                for ci in confirmed_interests:
                    cluster_meta[str(ci["cluster_id"])] = {
                        "label": ci["representative_topics"][0] if ci["representative_topics"] else "",
                        "status": ci["status"],
                    }

                for i, b in enumerate(embeddable):
                    cid = str(labels[standard_behaviors.index(b)]) if b in standard_behaviors else "-1"
                    meta = cluster_meta.get(cid, {"label": "Noise", "status": "Noise"})
                    embedding_map.append({
                        "x": round(float(coords[i, 0]), 4),
                        "y": round(float(coords[i, 1]), 4),
                        "cluster_id": cid,
                        "status": meta["status"],
                        "label": meta["label"],
                        "text": b.get("source_text", "")[:120],
                    })
                log.info("t-SNE embedding map built", extra={"user_id": user_id, "stage": "TSNE", "points": len(embedding_map)})
            else:
                log.warning("Too few embeddable behaviors for t-SNE", extra={"user_id": user_id, "count": len(embeddable)})
        except Exception as e:
            log.error("t-SNE computation failed", extra={"user_id": user_id, "error": str(e), "stage": "TSNE"})

        # 4. Finalizing Profile
        final_profile = {
            "user_id": user_id,
            "total_raw_behaviors": len(behaviors),
            "confirmed_interests": confirmed_interests,
            "embedding_map": embedding_map,
        }
        
        # 5. Generate Identity Anchor Prompt
        prompt_string = self.generate_identity_prompt(final_profile)
        final_profile["identity_anchor_prompt"] = prompt_string
        
        # 6. Save Output
        self.data_adapter.save_profile(user_id, final_profile)
        
        # Save prompt string to a .txt file
        prompt_path = os.path.join(self.data_adapter.output_dir, f"{user_id}_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_string)
        log.info("Identity Anchor prompt saved", extra={"user_id": user_id, "stage": "OUTPUT", "prompt_path": prompt_path})
        log.info("Pipeline execution complete", extra={"user_id": user_id, "stage": "COMPLETE", "confirmed_interests": len(confirmed_interests)})
        return final_profile

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the CBIE Pipeline.")
    parser.add_argument("--user_id", type=str, required=True, help="The User ID to process.")
    args = parser.parse_args()
    
    pipeline = CBIEPipeline()
    pipeline.process_user(args.user_id)
