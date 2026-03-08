import numpy as np
import spacy
import os
from openai import AzureOpenAI
from typing import List, Dict, Any, Tuple, Optional, Callable
from transformers import pipeline
import time
from sklearn.metrics.pairwise import cosine_distances

from logger import get_logger

log = get_logger(__name__)

class TopicDiscoverer:
    """
    Implements Stage 1 of the CBIE Methodology: Information Extraction & Topic Discovery.
    Uses Sentence Transformers for embeddings, HDBSCAN for clustering, and spaCy for domain adaptation.
    """

    def __init__(self, spacy_model: str = 'en_core_web_sm', zero_shot_model: str = 'facebook/bart-large-mnli', embedding_model_name: str = 'all-MiniLM-L6-v2'):
        log.info("Initializing Azure OpenAI Client for Chat", extra={"stage": "INIT"})
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("OPENAI_API_BASE")
        )
        self.chat_model = "gpt-4o-mini"
        
        log.info("Initializing SentenceTransformer", extra={"stage": "INIT", "model": embedding_model_name})
        from sentence_transformers import SentenceTransformer
        self.sentence_transformer = SentenceTransformer(embedding_model_name)
        # Using a deterministic embedding length 384 for all-MiniLM-L6-v2
        # Ensure we have a working chat model to fall back to
        self.chat_model = "gpt-4o-mini" # Confirmed to be available
        
        
        log.info("Loading Zero-Shot Classifier (BART)", extra={"stage": "INIT", "model": zero_shot_model})
        self.classifier = pipeline("zero-shot-classification", model=zero_shot_model)
        log.info("Zero-Shot Classifier loaded", extra={"stage": "INIT", "model": zero_shot_model})
        
        log.info("Loading spaCy NER model", extra={"stage": "INIT", "model": spacy_model})
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            log.warning("spaCy model not found, downloading", extra={"stage": "INIT", "model": spacy_model})
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", spacy_model], check=True)
            self.nlp = spacy.load(spacy_model)
        log.info("spaCy model loaded with EntityRuler", extra={"stage": "INIT", "model": spacy_model})
            
        # Initialize EntityRuler for domain adaptation
        self.ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        # Example domain-specific terms (this would ideally be configurable)
        patterns = [
            {"label": "TECH", "pattern": "kubernetes"},
            {"label": "TECH", "pattern": "docker"},
            {"label": "ALGO", "pattern": "dbscan"},
            {"label": "ALGO", "pattern": "hdbscan"}
        ]
        self.ruler.add_patterns(patterns)

    def process_behaviors(self, behaviors: List[Dict[str, Any]], progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], np.ndarray, np.ndarray]:
        """
        Takes raw behaviors, extracts entities, and isolates facts vs standard behaviors.
        Then clusters standard behaviors safely.
        Returns: (fact_behaviors, standard_behaviors, embeddings, cluster_labels)
        """
        if not behaviors:
            return [], [], np.array([]), np.array([])

        total = len(behaviors)

        # 1. Isolate Absolute Facts
        log.info("Starting fact isolation via Zero-Shot BART classifier", extra={"stage": "FACT_ISOLATION", "total": total})
        fact_behaviors, standard_behaviors = self.isolate_absolute_facts(behaviors, progress_callback=progress_callback)
        
        # 2. Process Standard Behaviors
        log.info("Extracting entities for standard behaviors", extra={"stage": "ENTITY_EXTRACTION", "count": len(standard_behaviors)})
        embeddings_list = []
        texts_to_embed = []
        indices_to_embed = []
        
        for i, b in enumerate(standard_behaviors):
            b['extracted_entities'] = self.extract_entities(b.get('source_text', ''))
            
            # Use precomputed if available
            emb = b.get('text_embedding')
            if emb is not None and isinstance(emb, np.ndarray) and len(emb) > 0:
                embeddings_list.append(emb)
            else:
                # Placeholder, will fill in next step
                embeddings_list.append(None)
                texts_to_embed.append(b.get('source_text', ''))
                indices_to_embed.append(i)
                
        # Generate missing embeddings
        if texts_to_embed:
            log.info("Generating missing embeddings via Azure OpenAI", extra={"stage": "EMBEDDINGS", "count": len(texts_to_embed)})
            new_embeddings = self.generate_embeddings(texts_to_embed)
            for idx, new_emb in zip(indices_to_embed, new_embeddings):
                embeddings_list[idx] = new_emb
        else:
            log.info("All embeddings precomputed — skipping Azure OpenAI call", extra={"stage": "EMBEDDINGS", "count": 0})
                
        # Format for clustering
        final_embeddings = np.array(embeddings_list)
        
        # 3. Cluster Behaviors
        labels = np.array([])
        if len(final_embeddings) > 0:
            log.info("Starting DBSCAN clustering", extra={"stage": "CLUSTERING", "vectors": len(final_embeddings)})
            polarities = [b.get('polarity', 'NEUTRAL') for b in standard_behaviors]
            labels = self.cluster_behaviors(final_embeddings, polarities)
            
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = int(np.sum(labels == -1))
            log.info("DBSCAN complete", extra={"stage": "CLUSTERING", "n_clusters": n_clusters, "n_noise": n_noise})
            
            # Attach labels
            for i, label in enumerate(labels):
                standard_behaviors[i]['cluster_id'] = int(label)
            
        return fact_behaviors, standard_behaviors, final_embeddings, labels

    def isolate_absolute_facts(self, behaviors: List[Dict[str, Any]], progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Separates absolute facts (permanent identity constraints like allergies, 
        dietary restrictions, medical conditions) from regular behavioral habits.
        
        Uses Zero-Shot NLP Classification to dynamically evaluate the text against 
        conceptual labels, completely eliminating hardcoded keyword arrays.
        """
        facts = []
        standards = []
        
        # We classify against generic conceptual labels rather than specific keywords
        candidate_labels = [
            "medical condition or severe allergy",
            "strict dietary restriction",
            "hobby or regular habit",
            "personal preference",
            "informational query"
        ]
        
        total = len(behaviors)
        for idx, b in enumerate(behaviors):
            # Report progress every behavior so the UI stays live
            if progress_callback:
                progress_callback("FACT_ISOLATION", idx + 1, total)
            # Log every 50 records to keep the terminal alive during long BART runs
            if idx % 50 == 0:
                log.info(
                    "Fact isolation in progress",
                    extra={"stage": "FACT_ISOLATION", "processed": idx, "total": total, "pct": round(idx / total * 100)}
                )
            
            text = b.get('source_text', '')
            fact_confidence = 0.0
            detection_reasons = []
            
            # ================================================================
            # LAYER 1: Zero-Shot Classification (Primary Signal)
            # ================================================================
            if text.strip():
                # multi_label=True ensures each label gets an independent probability (sigmoid) 
                # instead of competing against each other (softmax).
                result = self.classifier(text, candidate_labels, multi_label=True)
                scores_dict = dict(zip(result['labels'], result['scores']))
                
                # Check how strongly the model believes this is a fact-like concept
                med_score = scores_dict.get("medical condition or severe allergy", 0.0)
                diet_score = scores_dict.get("strict dietary restriction", 0.0)
                
                # We take the max confidence across the fact-like labels
                zero_shot_score = max(med_score, diet_score)
                fact_confidence += zero_shot_score
                
                if zero_shot_score > 0.5:
                    top_label = max(
                        ("medical condition", med_score),
                        ("dietary restriction", diet_score),
                        key=lambda x: x[1]
                    )[0]
                    detection_reasons.append(f"zero_shot_{top_label.replace(' ', '_')}: {zero_shot_score:.2f}")
            
            # ================================================================
            # LAYER 2: BAC Metadata (Secondary Confidence Boost Only)
            # ================================================================
            intent = b.get('intent', '').upper()
            polarity = str(b.get('polarity', '') or '').upper()
            
            if intent == "CONSTRAINT":
                fact_confidence += 0.1
                detection_reasons.append("bac_intent_constraint")
            
            if polarity == "NEGATIVE" and intent == "CONSTRAINT":
                fact_confidence += 0.05
                detection_reasons.append("bac_negative_constraint")
            
            # ================================================================
            # DECISION: Classify as Fact if combined confidence >= 0.70
            # ================================================================
            FACT_THRESHOLD = 0.70
            
            if fact_confidence >= FACT_THRESHOLD:
                b['fact_confidence'] = round(fact_confidence, 3)
                b['fact_detection_reasons'] = detection_reasons
                log.debug("Fact detected", extra={"stage": "FACT_ISOLATION", "text_preview": text[:60], "confidence": round(fact_confidence, 3), "reasons": detection_reasons})
                facts.append(b)
            else:
                standards.append(b)
                
        # Before returning, bundle all identified facts so they all map to a single unified "Medical/Dietary Restrictions" cluster conceptually
        for f in facts:
            f['cluster_id'] = "absolute_fact"
            # Instead of keeping their unique source texts separate, force their generalized topic to be unified during confirmation
            f['explicit_topics'] = [f.get('source_text', '')]
            
        log.info("Fact isolation complete", extra={"stage": "FACT_ISOLATION", "facts_found": len(facts), "standard_behaviors": len(standards)})
        return facts, standards

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extracts named entities using spaCy, including custom domain terms via EntityRuler.
        """
        doc = self.nlp(text)
        return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Vectorizes source_text using local sentence-transformers (e.g. all-MiniLM-L6-v2).
        Returns a (N, 384) dimension numpy array.
        """
        log.info("Generating embeddings locally with sentence-transformers", extra={"stage": "EMBEDDINGS", "count": len(texts)})
        embeddings = self.sentence_transformer.encode(texts, convert_to_numpy=True)
        return embeddings

    def generalize_cluster_topic(self, texts: List[str]) -> str:
        """
        Uses an LLM (gpt-4o-mini) to look at a list of raw behaviors in a cluster
        and return a generalized, cohesive 3-5 word trait/topic name.
        """
        # Just send a representative sample if the cluster is huge to save tokens
        sample = texts[:25] 
        prompt = (
            "You are an AI identity analyst building a behavioral profile for a user.\n"
            "Below is a list of their recent activities/queries that belong to a single cluster.\n"
            "Identify the cohesive, overarching theme connecting them and return a generalized "
            "classification label (maximum 4-5 words).\n\n"
            "Respond ONLY with the generalized label, nothing else.\n\n"
            "Examples:\n"
            " - 'Creating a custom middleware in FastAPI', 'Handling CORS issues in a Python API' -> Python Backend Development\n"
            " - 'Dune book review', 'Best sci-fi books' -> Science Fiction Literature\n"
            " - 'WDT distribution technique', 'How to text milk' -> Espresso Brewing\n\n"
            "Raw Behaviors:\n"
        )
        for t in sample:
            prompt += f"- {t}\n"
            
        log.info("Calling gpt-4o-mini to label cluster", extra={"stage": "TOPIC_LABELING", "sample_size": len(sample)})
        try:
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=20
            )
            label = response.choices[0].message.content.strip()
            log.info("Cluster label assigned", extra={"stage": "TOPIC_LABELING", "label": label})
            return label
        except Exception as e:
            log.error("Azure OpenAI Chat Error during topic labeling", extra={"stage": "TOPIC_LABELING", "error": str(e)})
            # Fallback to the most frequent string if LLM fails
            from collections import Counter
            counts = Counter(texts)
            return counts.most_common(1)[0][0]

    def cluster_behaviors(self, embeddings: np.ndarray, polarities: List[str] = None, min_cluster_size: int = 2, min_samples: int = 1) -> np.ndarray:
        """
        Uses HDBSCAN to find latent topic clusters.
        Applies a 'Polarity Penalty' to prevent POSITIVE and NEGATIVE sentiments
        from clustering together.
        Dynamic min_cluster_size scales with dataset size to prevent micro-clusters.
        """
        import hdbscan
        from sklearn.metrics.pairwise import euclidean_distances
        log.info("Building pairwise Euclidean distance matrix", extra={"stage": "CLUSTERING", "n": len(embeddings)})
        
        # Ensure we don't pass an empty array
        if len(embeddings) == 0:
            return np.array([])
            
        dist_matrix = euclidean_distances(embeddings).astype(np.float64)
        
        # Apply Polarity Penalty
        if polarities and len(polarities) == len(embeddings):
            n = len(embeddings)
            penalty_count = 0
            # HDBSCAN operates on distance. We set opposing polarities to maximum possible float
            max_penalty = 1000.0 
            for i in range(n):
                for j in range(i+1, n):
                    p1 = str(polarities[i] or '').upper()
                    p2 = str(polarities[j] or '').upper()
                    
                    if (p1 == 'POSITIVE' and p2 == 'NEGATIVE') or (p1 == 'NEGATIVE' and p2 == 'POSITIVE'):
                        dist_matrix[i, j] = max_penalty
                        dist_matrix[j, i] = max_penalty
                        penalty_count += 1
            log.info("Polarity penalty applied to distance matrix", extra={"stage": "CLUSTERING", "penalized_pairs": penalty_count})

        # --- FIX: Dynamic min_cluster_size ---
        # Scale the minimum cluster size with the dataset.
        # Rule: a cluster must contain at least 10% of behaviors OR 3, whichever is larger.
        # This prevents single-query one-offs from being confirmed as "stable" interests.
        n_behaviors = len(embeddings)
        actual_min_cluster = max(3, n_behaviors // 10)
        log.info("Running HDBSCAN", extra={"stage": "CLUSTERING", "min_cluster_size": actual_min_cluster, "n_behaviors": n_behaviors})
        
        clusterer = hdbscan.HDBSCAN(min_cluster_size=actual_min_cluster, min_samples=min_samples, metric='precomputed')
        return clusterer.fit_predict(dist_matrix)
