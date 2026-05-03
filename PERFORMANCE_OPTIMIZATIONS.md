# CBIE Engine Performance Optimizations & Known Limitations

This document outlines the known physical resource bottlenecks of the Core Behaviour Analysis Component (CBAC) at scale, alongside the identified, minimal technical fixes required to resolve them in a production environment. 

Since the primary goal of this research prototype is robust methodological validation (prioritizing accuracy and temporal confirmation algorithms), these optimizations are intentionally deferred.

---

## 1. Zero-Shot NLP CPU Bottleneck (Latency Constraint)

**The Bottleneck:**
The pipeline currently utilizes the `facebook/bart-large-mnli` model (~1.5 GB) for zero-shot text classification during the Fact Isolation stage. Since the engine runs on a standard CPU, text processing tensor operations are incredibly slow and represent the absolute dominant latency factor in the pipeline.

**Minimal Fix:**
Swap the massive BART model for a smaller, CPU-optimized "distilled" model. `typeform/distilbert-base-uncased-mnli` requires only ~250MB of RAM and executes inference roughly 400% to 500% faster on a CPU, while retaining ~95% of the accuracy.

*Implementation Change:*
In `src/cbie_engine/topic_discovery.py` (~Line 20):
```python
# Change from:
def __init__(self, spacy_model: str = 'en_core_web_sm', zero_shot_model: str = 'facebook/bart-large-mnli', embedding_model_name: str = 'all-MiniLM-L6-v2'):

# Change to:
def __init__(self, spacy_model: str = 'en_core_web_sm', zero_shot_model: str = 'typeform/distilbert-base-uncased-mnli', embedding_model_name: str = 'all-MiniLM-L6-v2'):
```
> **Research Note:** If implementing this fix, the hardcoded `FACT_THRESHOLD = 0.70` logic must be slightly re-calibrated against the manually annotated Ground Truth dataset, as the raw confidence logit distribution differs slightly between BERT and BART architectures.

---

## 2. Vector Similarity Sequential Scan (Throughput Constraint)

**The Bottleneck:**
The current Supabase PostgreSQL instance utilizes the `pgvector` extension for behavior storage, but no spatial index has been applied to the vector embeddings. Consequently, vector similarity searches (e.g., Euclidean distance calculations or $K$-Nearest Neighbor lookups) degrade to $O(N)$ Sequential Scans. Beyond ~100,000 behaviors per user profile, this scan becomes prohibitively slow. 

**Minimal Fix:**
Apply a Hierarchical Navigable Small World (HNSW) index to the database. This converts the search to an Approximate Nearest Neighbor (ANN) algorithm, reducing time complexity to $O(\log N)$ for a massive architectural speedup.

*Implementation Change:*
Execute the following SQL command in the Database console:
```sql
CREATE INDEX ON public.behaviors USING hnsw (text_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 3. Excessive Docker Image Footprint (Storage Constraint)

**The Bottleneck:**
The generated Docker Image for the `cbie_engine` sits at approximately 12GB. This is heavily artificially inflated because the standard `pip install torch` command downloads massive NVIDIA CUDA and cuDNN binaries. Because the container strictly runs on CPU, these GPU drivers are entirely redundant.

**Minimal Fix:**
Force the Python package manager to download the CPU-only version of PyTorch.

*Implementation Change:*
In `cbie_engine/requirements.txt`, prepend the PyTorch CPU wheels registry before the existing torch requirement. This reduces the final Docker image footprint down to ~2GB.

```text
transformers>=4.35.0
--extra-index-url https://download.pytorch.org/whl/cpu
torch>=2.1.0
kneed>=0.8.5
```
