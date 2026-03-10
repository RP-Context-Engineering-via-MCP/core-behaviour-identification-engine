# Core Behaviour Identification Engine (CBIE) — System Documentation

> **Version:** 2.1  
> **Author:** DAYANANDA G.A.C.T  
> **Project:** Core Behaviour Analysis Component (CBAC) — Research Prototype  
> **Last Updated:** March 2026

---

## 1. Overview

The **Core Behaviour Identification Engine (CBIE)** is an offline, batch-processing analytical engine designed to analyze a user's entire interaction history and distill it into a stable **Core Behaviour Profile**. This profile serves as a persistent, high-fidelity identity anchor for Large Language Models (LLMs), enabling deep personalization across sessions.

The CBIE is exposed as a **FastAPI microservice**, allowing integration with LLM orchestration layers and frontend dashboards via a well-defined REST API.

### 1.1 The Problem

LLMs are stateless by nature. Every conversation starts from scratch, with no memory of who the user is, what they care about, or what they need. While a real-time **Behavior Analysis Component (BAC)** can log individual events and their dynamic scores, it produces raw, noisy data that fluctuates constantly. The CBIE solves this by acting as an offline "analyst" that processes the entire history of BAC logs to find **meaningful, long-term patterns**.

### 1.2 Key Distinction: BAC vs. CBIE

| Component | Role | Processing | Output |
|-----------|------|------------|--------|
| **BAC** | Real-time "sensor" | Logs individual events with dynamic scores (credibility, clarity, decay) | Raw behavioral event stream |
| **CBIE** | Offline "analyst" | Batch-processes the entire history to find stable patterns | Core Behaviour Profile (JSON) + Identity Anchor Prompt |

### 1.3 What the CBIE Produces

A single JSON document per user — the **Core Behaviour Profile** — containing:
- **Stable Facts**: Permanent identity constraints (e.g., allergies, dietary restrictions)
- **Stable Interests**: Confirmed, long-term behavioral patterns (e.g., "interested in machine learning")
- **Emerging Interests**: Growing but not yet confirmed patterns (e.g., "recently exploring photography")
- **ARCHIVED_CORE**: Historical habits that have faded but are kept on record
- **Noise**: Discarded one-off queries that don't represent real interests

And a compiled **Identity Anchor Prompt** — a plain-English system message ready to be injected into an LLM call.

---

## 2. System Architecture

```mermaid
graph TD
    subgraph LLM["LLM Orchestration Layer"]
        LLMC[LLM Chat Service]
    end

    subgraph FE["Frontend Dashboard"]
        UI[React / Next.js Admin App]
        V1[t-SNE Embedding Map]
        V2[Radar Scoring Chart]
        UI --- V1
        UI --- V2
    end

    subgraph API["CBIE Microservice — FastAPI :6009"]
        direction TB
        GW[FastAPI App / main.py]
        CTX["GET /context/{user_id} ★"]
        ADM["GET /admin/..."]
        PIP["POST /admin/users/{user_id}/run_pipeline"]
        STAT["GET /admin/jobs/{job_id}"]
        PROF["GET /profiles/..."]
    end

    subgraph Engine["CBIE Core Engine"]
        DA[DataAdapter]
        TD[TopicDiscoverer - Stage 1]
        TA[TemporalAnalyzer - Stage 2]
        CM[ConfirmationModel - Stage 3]
        PL[CBIEPipeline]
    end

    subgraph DB["Supabase PostgreSQL + pgvector"]
        BT[(BAC Database: behaviors)]
        PT[(CBIE Database: profiles)]
    end

    LLMC -- "GET /context/{user_id}" --> CTX
    UI -- "POST run_pipeline" --> PIP
    UI -- "GET profile / stats" --> ADM
    UI -- "Polling status" --> STAT

    GW --> CTX & ADM & PIP & STAT & PROF
    CTX & PIP --> PL
    PL --> DA & TD & TA & CM
    DA <-->|"read / write"| DB

    style CTX fill:#D94A7A,color:#fff
    style DB fill:#3ECF8E,color:#fff
    style UI fill:#6366F1,color:#fff

### 2.2 Dual-Database Isolation & Data Adapter

To ensure architectural decoupling and respect the production-grade separation of concerns, the CBIE initializes two independent Supabase clients within the `DataAdapter` class:

1. **BAC Database (Read-Only)**: Configured via `BAC_SUPABASE_URL`. This serves as the primary data source for raw interaction events.
2. **CBIE Database (Read/Write)**: Configured via `SUPABASE_URL`. This acts as the dedicated analytical store for generated profiles and processing checkpoints.

**Automatic Data Adaptation:**
The `DataAdapter` performs schema-alignment on the fly, transforming the BAC's native `bigint` (Unix epoch milliseconds) timestamps into standardized ISO-8601 strings, ensuring full compatibility with the downstream temporal analysis modules.


### 2.1 Component Overview

| File | Class | Stage | Responsibility |
|------|-------|-------|----------------|
| `data_adapter.py` | `DataAdapter` | Ingestion / Output | Reads `behaviors` from **BAC Supabase**, writes profiles to **CBIE Supabase** |
| `topic_discovery.py` | `TopicDiscoverer` | Stage 1 | Fact isolation (Zero-Shot NLP), Azure embeddings, **Adaptive DBSCAN clustering**, LLM topic labeling |
| `temporal_analysis.py` | `TemporalAnalyzer` | Stage 2 | Gini Coefficient (consistency), Mann-Kendall Trend Test (momentum) |
| `confirmation_model.py` | `ConfirmationModel` | Stage 3 | AHP-weighted heuristic scoring, Vitality Pruning, status classification |
| `pipeline.py` | `CBIEPipeline` | Orchestration | Ties all stages together; supports **Incremental Checkpoint Processing** |
| `api/main.py` | FastAPI app | API Layer | App entry point, CORS, lifespan startup, health endpoints |
| `api/dependencies.py` | — | API Layer | Pipeline singleton (load-once), in-memory job store for background runs |
| `api/models.py` | Pydantic models | API Layer | All request/response schemas |
| `api/routers/context.py` | — | API Layer | `GET /context/{user_id}` — the critical LLM endpoint |
| `api/routers/pipeline_router.py` | — | API Layer | `POST /pipeline/run`, `GET /pipeline/status` |
| `api/routers/profiles.py` | — | API Layer | Profile CRUD and inspection endpoints |
| `generate_test_data.py` | — | Testing | Generates multi-user test data with Azure embeddings, seeds to Supabase |

---

## 3. Data Pipeline

### 3.1 Input Schema (Supabase `behaviors` table)

Each row represents a single behavioral event logged by the BAC. The CBIE **only reads rows where `behavior_state = 'ACTIVE'`**, respecting the BAC's conflict resolution so that SUPERSEDED and FLAGGED behaviors are never analyzed.

| Column | Type | Description |
|--------|------|-------------|
| `behavior_id` | `TEXT (PK)` | Unique identifier |
| `user_id` | `TEXT` | The owning user |
| `behavior_text` | `TEXT` | Raw natural language text of the behavior |
| `embedding` | `vector(3072)` | Pre-computed semantic embedding (Azure `text-embedding-3-large`) |
| `credibility` | `REAL` | BAC-assigned credibility (0.0 – 1.0) |
| `clarity_score` | `REAL` | Clarity of expression (0.0 – 1.0) |
| `extraction_confidence` | `REAL` | BAC extraction confidence (0.0 – 1.0) |
| `intent` | `TEXT` | `PREFERENCE`, `CONSTRAINT`, `HABIT`, `SKILL`, `QUERY`, `COMMUNICATION` |
| `target` | `TEXT` | Subject/object of the behavior |
| `context` | `TEXT` | Domain (e.g., `tech`, `health`, `food`) |
| `polarity` | `TEXT` | `POSITIVE` or `NEGATIVE` |
| `created_at` | `TIMESTAMPTZ` | When first recorded |
| `decay_rate` | `REAL` | Rate of relevance decay (0.0 for facts) |
| `reinforcement_count` | `INTEGER` | Number of times expressed |
| `behavior_state` | `TEXT` | `ACTIVE` \| `SUPERSEDED` \| `FLAGGED` \| `DECAYED` |

### 3.2 Output Schema (Supabase `core_behavior_profiles` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | `SERIAL (PK)` | Auto-incrementing PK |
| `user_id` | `TEXT (UNIQUE)` | The owning user |
| `total_raw_behaviors` | `INTEGER` | Number of input behaviors processed |
| `confirmed_interests` | `JSONB` | Array of confirmed interest cluster objects |
| `identity_anchor_prompt` | `TEXT` | Pre-compiled system prompt for LLMs |
| `created_at` | `TIMESTAMPTZ` | Profile creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | Last regeneration timestamp |
| `last_processed_timestamp` | `TIMESTAMPTZ` | The checkpoint marker used for incremental logic |

### 3.3 Incremental Checkpoint Processing

To optimize performance and avoid redundant $O(n^2)$ distance matrix computations, the CBIE implements a **Checkpoint Marker** system:

1. **Checkpoint Fetch**: The pipeline retrieves the `last_processed_timestamp` from the user's core profile.
2. **Delta Fetch**: The `DataAdapter` queries the BAC database for only those behaviors created *after* the checkpoint.
3. **Threshold Gate**: If the number of new behaviors is less than **10** (`MIN_NEW_BEHAVIORS`), the pipeline run is gracefully skipped to conserve compute resources.
4. **Manual Override**: The system supports the `force_full_run=True` flag to ignore checkpoints and re-analyze the entire 500-behavior window from scratch.

Each object in the `confirmed_interests` JSONB array:

```json
{
    "cluster_id": "absolute_fact" | "0" | "1" | "2",
    "representative_topics": ["Python Backend Development"],
    "frequency": 7,
    "consistency_score": 0.12,
    "trend_score": 0.0,
    "core_score": 0.85,
    "avg_credibility": 0.92,
    "status": "Stable" | "Emerging" | "Stable Fact" | "ARCHIVED_CORE" | "Noise"
}
```

---

## 4. Technical Methodology

### 4.1 Stage 1: Topic Discovery & Fact Isolation (`TopicDiscoverer`)

#### 4.1.1 Absolute Fact Isolation (Zero-Shot NLP Detection)

Before clustering, every behavior's raw text is passed through a **multi-layer fact detection pipeline** to identify permanent identity constraints (allergies, dietary restrictions, medical conditions).

> **Key Design Decision:** The CBIE does NOT use the BAC's `intent` field as the sole signal, nor does it use brittle hardcoded keyword arrays. It uses a **Zero-Shot NLP Classifier** (`facebook/bart-large-mnli`) to dynamically evaluate semantic meaning. For performance, behaviors are processed in **batches of 32**, yielding a 10x throughput improvement over sequential inference.

**Two-Layer Detection Strategy:**

| Layer | Signal | Weight |
|-------|--------|--------|
| **Zero-Shot NLP** (Primary) | Scores text against `"medical condition or severe allergy"`, `"strict dietary restriction"` using `multi_label=True` | Max score across the two labels |
| **BAC Metadata** (Secondary Boost) | If `intent == CONSTRAINT`: +0.10. If `polarity == NEGATIVE` AND `intent == CONSTRAINT`: additional +0.05 | Additive boost only |

**Decision Rule:** If combined `fact_confidence ≥ 0.70` → classified as **Absolute Fact**.

**Example detection trace:**
```
Input: "I am severely allergic to penicillin"
  Zero-Shot "medical condition or severe allergy" → 0.92
  BAC intent = CONSTRAINT                         → +0.10
  BAC polarity = NEGATIVE                         → +0.05
  ─────────────────────────────────────────────────
  Total fact_confidence = 1.07  (≥ 0.70) → FACT ✓
```

Facts are immediately routed to the profile with `core_score = 1.0` and `status = "Stable Fact"`. No temporal analysis is needed.

#### 4.1.2 Semantic Embeddings (Azure OpenAI `text-embedding-3-large`)

All remaining (non-fact) behaviors are embedded using Azure OpenAI's `text-embedding-3-large` model, producing **3072-dimensional** semantic vectors. If the database already contains precomputed embeddings, they are reused. Missing embeddings are generated in batches of 20.

- **Model:** `text-embedding-3-large`
- **Dimensions:** 3072
- **Storage:** pgvector `vector(3072)` column in Supabase

#### 4.1.3 Entity Extraction (spaCy + EntityRuler)

Each behavior's text is processed through spaCy's NER pipeline (`en_core_web_sm`), extended with a custom **EntityRuler** for domain-specific terms (e.g., `kubernetes` → `TECH`, `hdbscan` → `ALGO`).

#### 4.1.4 Adaptive Density-Based Clustering (DBSCAN)

Clusters standard behaviors using **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) with a mathematically derived **Adaptive Epsilon**.

1. **Base Matrix:** Pairwise Euclidean distances.
2. **Polarity Penalty:** If two behaviors have opposite sentiments (`POSITIVE` vs `NEGATIVE`), their distance is artificially set to `1000.0`.
3. **Adaptive Epsilon (k-distance graph):** 
   - Uses the distance to the $k$-th nearest neighbor ($k=min\_samples$) to generate a k-distance plot.
   - Automatically identifies the "elbow" or "knee" point using the `kneed` library.
   - **Semantic Boundary Cap:** Epsilon is strictly capped at **0.75** (max) and **0.20** (min). This ensures that clusters only form when behaviors are semantically tight (dist ≤ 0.75 ≈ cos sim ≥ 0.72), preventing the formation of overly generic "mega-clusters".

> **Why DBSCAN with Adaptive Epsilon?** This method ensures high-precision semantic islands. While HDBSCAN is density-invariant, it often merges distinct but slightly related behavioral groups in sparse datasets. Adaptive DBSCAN maintains strict semantic boundaries, crucial for identifying specific user habits (e.g., "Dog Walking") rather than generic categories.

Behaviors assigned `cluster_id = -1` are classified as **noise** and excluded from the profile.

#### 4.1.5 Dual-Gate Noise Filtering & Semantic Guardrails

Before confirmation, clusters undergo three primary high-fidelity noise checks:

1. **Semantic Contradiction Suppression**: Any cluster whose mean embedding is semantically opposite to a confirmed **Stable Fact** is suppressed.
2. **The "Trivia Gate"**: Individual behaviors are scored by the BART Zero-Shot classifier for being `"random trivia or one-off query"`. If a cluster’s average trivia score exceeds **0.80**, it is flagged as noise.
3. **Structural Complexity Check**: Behaviors with a `clarity_score` below **0.65** (indicative of messy, low-signal extraction) are used for clustering but given low weights during the final core-score derivation.

#### 4.1.5 Generative Topic Labeling (Azure OpenAI `gpt-4o-mini`)

After clustering, the raw behavior texts of each standard cluster are passed to `gpt-4o-mini` with a structured prompt asking for a single cohesive trait label (max 4-5 words). This replaces raw query strings like `"Creating a custom middleware in FastAPI"` with high-level traits like `"Python Backend Development"`.

> **Note on Absolute Facts:** Absolute Facts skip this LLM generalization step. To ensure the LLM strictly adheres to safety-critical constraints, their exact raw text (e.g., `"cannot eat peanuts"`) is injected directly into the Core Profile. This prevents multiple specific constraints from being merged into unhelpful generic labels like "Food Preferences".

### 4.4 Data Visualization Engine (t-SNE)

To bridge the gap between high-dimensional math and administrative clarity, the pipeline includes a **Visualization Lithography** stage.

1. **Projection**: It uses **t-SNE** (t-distributed Stochastic Neighbor Embedding) to project the 3072-dimensional Azure embeddings into a **2D space**.
2. **Perplexity Mapping**: A dynamic perplexity is chosen based on the number of behaviors to ensure stable local structure.
3. **The Embedding Map**: Returns an array of `{x, y, label, status}` objects, which are cached in the profile JSON.
4. **Dashboard Utility**: This map enables the "Semantic Space" scatter chart in the admin dashboard, allowing researchers to visually verify that clustered behaviors are actually grouped correctly in vector space.

---

### 4.2 Stage 2: Temporal Analysis (`TemporalAnalyzer`)

#### 4.2.1 Consistency — Gini Coefficient

Measures the uniformity of time intervals between behaviors in a cluster.

**How it works:**
1. Sort all cluster timestamps chronologically
2. Compute inter-event time gaps (in days)
3. Apply the Gini Coefficient formula

**Interpretation:**

| Gini | Meaning |
|------|---------|
| `0.0` | Perfectly consistent (equal intervals) |
| `0.3` | Fairly consistent |
| `0.8+` | Burst activity, then long silence |
| `1.0` | Single data point — cannot determine |

**Formula:**

$$G = \frac{\sum_{i=1}^{n}(2i - n - 1) \cdot x_i}{n \cdot \sum_{i=1}^{n} x_i}$$

Where $x_i$ are the **sorted** inter-event times and $n$ is the number of intervals.

> The Gini score is **inverted** in Stage 3: lower Gini (more consistent) → higher contribution to the final score.

#### 4.2.2 Trend — Mann-Kendall Test

A non-parametric statistical test applied to the sequence of `complexity_score` values within a cluster over time to detect monotonic trends.

| Result | Trend Score | Meaning |
|--------|-------------|---------|
| `increasing` | `1.0` | Deepening engagement |
| `decreasing` | `-1.0` | Fading interest |
| `no trend` | `0.0` | No significant change |

Requires ≥ 4 data points; otherwise defaults to `0.0`.

---

### 4.3 Stage 3: Confirmation Model (`ConfirmationModel`)

#### 4.3.1 AHP-Weighted Heuristic Score

Combines all signals into a final `core_score` using AHP-derived weights:

| Factor | Weight | Source | Normalization |
|--------|--------|--------|---------------|
| **Consistency** | `0.35` | Gini (Stage 2) | `1.0 - Gini` (inverted) |
| **Credibility** | `0.30` | Avg BAC credibility across cluster | Already 0.0 – 1.0 |
| **Frequency** | `0.25` | Cluster size / max cluster size | Relative 0.0 – 1.0 |
| **Trend** | `0.10` | Mann-Kendall result (Stage 2) | `(score + 1.0) / 2.0` |

**Formula:**

$$\text{CoreScore} = (0.35 \times (1 - G)) + (0.30 \times C) + \left(0.25 \times \frac{f}{f_{max}}\right) + \left(0.10 \times \frac{T + 1}{2}\right)$$

Where: $G$ = Gini, $C$ = avg credibility, $f$ = cluster frequency, $f_{max}$ = largest cluster size, $T$ = trend score.

> Weights derived via **Analytic Hierarchy Process (AHP)**. Consistency is weighted highest as repeated engagement is the strongest signal of a core long-term behavior.

#### 4.3.2 Status Classification (Vitality Pruning)

| Core Score | Status | LLM Treatment |
|------------|--------|---------------|
| `≥ 0.70` | **Stable** | Included in active context window |
| `0.40 – 0.69` | **Emerging** | Included in active context window with caveat |
| `0.15 – 0.39` | **Noise** | Excluded from profile entirely |
| `< 0.15` | **ARCHIVED_CORE** | Kept in DB for historical record but excluded from LLM prompt |
| _(any, if fact)_ | **Stable Fact** | Permanently injected into `CRITICAL CONSTRAINTS` section |

#### 4.3.3 Summary of Classification Logic

To ensure research rigor, the following thresholds are strictly enforced by the CBIE:

| Category | Detection Mechanism | Primary Threshold | Signal Sources |
| :--- | :--- | :--- | :--- |
| **Active Facts** (Stable Fact) | Multi-layer Zero-Shot Inference | `fact_confidence ≥ 0.70` | BART-Large-MNLI + BAC `CONSTRAINT` intent + Negative Polarity |
| **Stable Interests** | AHP-Weighted Heuristic Scoring | `core_score ≥ 0.70` | Gini Consistency (0.35) + Credibility (0.30) + Freq (0.25) + Trend (0.10) |
| **Emerging Interests** | AHP-Weighted Heuristic Scoring | `0.40 ≤ core_score < 0.70` | Same as above; indicates growing patterns or moderate consistency |
| **Core Interests** | Collective grouping | `core_score ≥ 0.40` | The union of **Stable** and **Emerging** interests used for context injection |
| **Noise / Archived** | Vitality Pruning | `core_score < 0.40` | Discarded as one-off queries or historical artifacts |

---

## 5. Pipeline Execution Flow

```
Step 1: INGESTION
  └─ DataAdapter → Supabase
  └─ SELECT * FROM behaviors WHERE user_id = ? AND behavior_state = 'ACTIVE'
  └─ Parses embeddings (string → numpy), credibility, timestamps, polarity
  └─ Returns time-sorted list of behavior dicts

Step 2: TOPIC DISCOVERY (Stage 1)
  ├─ Zero-Shot NLP Classification → Isolate Absolute Facts
  │     ├─ Facts bypass all scoring → core_score = 1.0, status = "Stable Fact"
  │     └─ Facts bypass LLM generalization; raw text is used directly
  └─ Standard Behaviors:
        ├─ spaCy NER + EntityRuler → extracted entities
        ├─ Use precomputed embeddings (or generate via Azure if missing)
        ├─ Build Euclidean distance matrix
        ├─ Build Euclidean distance matrix
        ├─ Apply Polarity Penalty (POSITIVE vs NEGATIVE → distance = 1000)
        ├─ Adaptive Epsilon calculation via k-distance graph (capped at 0.75)
        ├─ DBSCAN(eps=adaptive, min_samples=2) → cluster_id per behavior
        └─ gpt-4o-mini → cohesive 4-5 word topic label per cluster

Step 3: TEMPORAL ANALYSIS (Stage 2) — per cluster
  ├─ Compute inter-event time gaps from timestamps
  ├─ Gini Coefficient → consistency_score
  └─ Mann-Kendall Test on scores → trend_score

Step 4: CONFIRMATION (Stage 3) — per cluster
  ├─ Average BAC credibility across cluster
  ├─ AHP core_score = (0.35 × consistency) + (0.30 × credibility) +
  │                   (0.25 × frequency) + (0.10 × trend)
  └─ Vitality Pruning → Stable | Emerging | Noise | ARCHIVED_CORE

Step 5: PROMPT GENERATION
  ├─ generate_identity_prompt() compiles interests by status into a human-readable
  │   system message string (Critical Constraints, Stable, Emerging, Archived)
  └─ identity_anchor_prompt stored in profile JSON and Supabase

Step 6: DATA VISUALIZATION LITHOGRAPHY
  ├─ t-SNE Dimensionality Reduction: Projects 384D/3072D embeddings into 2D (x, y)
  ├─ Generates Embedding Map: {x, y, cluster_id, status, label, text}
  └─ Saved to local profile JSON for near-instant dashboard rendering

Step 7: OUTPUT
  ├─ Save Core Behaviour Profile JSON → data/profiles/<user_id>_profile.json
  ├─ Save Identity Anchor text → data/profiles/<user_id>_prompt.txt
  └─ UPSERT into Supabase core_behavior_profiles (on_conflict: user_id)
```

---

## 6. REST API Reference (FastAPI Microservice)

The CBIE is deployed as a FastAPI microservice. All endpoints are documented interactively at **`http://localhost:6009/docs`** (Swagger UI).

### 6.1 LLM Context Endpoint ⭐

This is the single most critical integration point — the LLM's chat service calls this before every AI response to retrieve the user's identity anchor.

#### `GET /context/{user_id}`

Reads the pre-built Identity Anchor Prompt from `core_behavior_profiles`. **No pipeline re-run is triggered** — designed for near-instant latency.

**Response** `200 OK`:
```json
{
    "user_id": "user_alpha_01",
    "identity_anchor_prompt": "--- SYSTEM IDENTITY ANCHOR FOR USER: user_alpha_01 ---\n...",
    "profile_exists": true,
    "total_raw_behaviors": 105,
    "last_updated": "2026-02-27T04:15:00Z"
}
```
Returns `404` if no profile exists; returns `503` if the database is unavailable.

---

### 6.2 Pipeline Endpoints

Because the CBIE pipeline can take **several minutes** (Zero-Shot NLP model is CPU-bound), all runs are **asynchronous background jobs**.

#### `POST /pipeline/run/{user_id}` — `202 Accepted`

Queues a full CBIE analysis for a user and returns immediately with a `job_id`.

**Response:**
```json
{
    "job_id": "a1b2c3d4-...",
    "status": "QUEUED",
    "user_id": "user_spartan_02",
    "message": "Pipeline run queued. Poll GET /pipeline/status/a1b2c3d4-..."
}
```

#### `GET /pipeline/status/{job_id}`

Polls the status of a queued pipeline run.

**Response:**
```json
{
    "job_id": "a1b2c3d4-...",
    "user_id": "user_spartan_02",
    "status": "COMPLETED",
    "started_at": "2026-02-27T04:10:00Z",
    "completed_at": "2026-02-27T04:14:32Z",
    "result": { "user_id": "...", "confirmed_interests": [...] },
    "error": null
}
```
| Status | Meaning |
|--------|---------|
| `QUEUED` | Job accepted, not yet started |
| `RUNNING` | Pipeline actively processing |
| `COMPLETED` | Profile saved; `result` contains the full profile JSON |
| `FAILED` | Error occurred; see `error` field |

---

### 6.3 Profile Endpoints (Frontend Dashboard)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/profiles/` | Paginated list of all users with profiles (`?limit=50&offset=0`) |
| `GET` | `/profiles/{user_id}` | Full Core Behaviour Profile JSON for a user |
| `GET` | `/profiles/{user_id}/interests` | Only the `confirmed_interests` array (supports `?status_filter=Stable`) |
| `GET` | `/profiles/{user_id}/facts` | Only interests with `status = "Stable Fact"` (for constraint alert panels) |
| `DELETE` | `/profiles/{user_id}` | Delete profile from Supabase and local JSON file (`204 No Content`) |

**`GET /profiles/` — Response:**
```json
{
    "total": 3,
    "profiles": [
        {
            "user_id": "user_alpha_01",
            "total_raw_behaviors": 105,
            "interest_count": 14,
            "fact_count": 5,
            "stable_count": 6,
            "emerging_count": 3,
            "last_updated": "2026-02-27T04:15:00Z"
        }
    ]
}
```

---

### 6.4 Admin API Endpoints (Frontend Dashboard)

The admin endpoints allow an internal dashboard to discover users, inspect raw behaviors, and manually trigger pipeline runs without modifying existing public API behavior.

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/admin/users` | Lists all users with ACTIVE behaviors, showing total behavior count and if a profile exists. |
| `GET`  | `/admin/users/{user_id}` | Combines behavior stats with profile summary stats for a single user. |
| `GET`  | `/admin/users/{user_id}/profile` | Returns the full Core Behaviour Profile formatted with distinct categories (Critical Constraints, Stable, Emerging, Archived, Noise Counts). |
| `GET`  | `/admin/users/{user_id}/behaviors` | Returns raw `behaviors` rows (excluding embeddings) for data preview (`?limit=50&offset=0`). |
| `GET`  | `/admin/users/{user_id}/embedding-map` | Returns pre-computed 2D t-SNE coordinates for each behavior embedding (generated during pipeline run). |
| `POST` | `/admin/users/{user_id}/run_pipeline` | Thin wrapper around pipeline execution; triggers an async job and returns a `job_id`. |
| `GET`  | `/admin/jobs/{job_id}` | Polls the current status of a pipeline run, including real-time stage and progress counts (e.g., "Classifying 32 / 300"). |

---

### 6.5 Health & Service Info

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns `{"status": "ok", "pipeline_ready": true/false}` |
| `GET` | `/` | Returns service name, version, and doc links |

---

### 6.6 API Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Pipeline Singleton** | The BART zero-shot model (~1.5 GB) is loaded **once** at app startup via a `lifespan` context manager. All requests share the same instance to avoid re-loading on every call. |
| **Background Tasks** | `FastAPI.BackgroundTasks` runs the CPU-bound pipeline in a thread-pool executor (`loop.run_in_executor`), freeing the async event loop for other requests. |
| **In-Memory Job Store** | Sufficient for a research prototype. Easily replaceable with Redis/Celery in production. |
| **CORS: allow all** | Frontend domain not yet finalized — tighten once the frontend URL is known. |
| **`/context` reads DB only** | The LLM endpoint does NOT re-run the pipeline; it reads cached data for millisecond latency. The pipeline must be explicitly triggered via `POST /pipeline/run`. |

---

## 7. Example Output

For `user_alpha_01` (105 behaviors across varied domains):

**Identity Anchor Prompt (injected into LLM system message):**
```text
--- SYSTEM IDENTITY ANCHOR FOR USER: user_alpha_01 ---
You are speaking with a user who has following core traits and constraints.

CRITICAL CONSTRAINTS (Never violate):
- Penicillin Allergy Constraint
- Strict Vegan Diet
- Asthma Management
- Weekend Work Restriction
- Celiac Disease (No Gluten)

VERIFIED STABLE PREFERENCES:
- React Frontend Development
- Python Backend Development (FastAPI)
- Espresso Preparation and Techniques
- Django Framework Criticisms

EMERGING INTERESTS (Needs more verification):
- Science Fiction Literature
- Personal Finance Optimization
```

**Edge-case validation results:**

| User | Behaviors | Result |
|------|-----------|--------|
| `user_spartan_02` | 12 (focused) | 1 Stable interest: `Barefoot Running Techniques` |
| `user_chaos_03` | 149 (120 pure noise) | 120 noise vectors discarded; 2 constraints + 3 emerging found correctly |

---

## 8. Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Core language |
| `fastapi` | ≥ 0.111.0 | REST API framework |
| `uvicorn` | ≥ 0.29.0 | ASGI server |
| `openai` | ≥ 1.0.0 | Azure embeddings and GPT-4o-mini topic labeling |
| `transformers` | ≥ 4.35.0 | Zero-Shot classifier (`facebook/bart-large-mnli`) |
| `kneed` | ≥ 0.8.5 | Mathematical detection of knee/elbow points for adaptive epsilon |
| `scikit-learn` | ≥ 1.3.0 | DBSCAN clustering, t-SNE dimensionality reduction & distance metrics |
| `pymannkendall` | ≥ 1.4.3 | Mann-Kendall Trend Test |
| `supabase` | ≥ 2.3.4 | Cloud DB client (PostgreSQL + pgvector) |
| Next.js | 15.x | Admin Dashboard framework |
| Tailwind CSS | 4.x | Styling and layout |
| Recharts | ≥ 3.8.0 | Data visualizations (Scatter & Radar charts) |

---

## 9. Project Structure

```
cbie_engine/
│
├── .env                              # API keys
├── requirements.txt                  # Python dependencies
│
├── pipeline.py                       # Orchestrator & Prompt Gen
├── topic_discovery.py                # Stage 1: Zero-Shot, HDBSCAN, GPT labeling
├── temporal_analysis.py              # Stage 2: Gini + Mann-Kendall
├── confirmation_model.py             # Stage 3: AHP scoring + Vitality Pruning
│
├── api/                              # FastAPI Microservice
│   ├── main.py                       # Entry point
│   ├── models.py                     # Pydantic models
│   └── routers/                      # Route handlers
│
├── admin-dashboard/                  # Next.js Admin Panel
│   ├── src/app                       # Pages & Routing
│   ├── src/components                # Recharts & UI Components
│   └── tailwind.config.ts            # Styling configuration
│
└── data/
    └── profiles/                     # Local profile & t-SNE json outputs
```

---

## 10. Environment Variables (`.env`)

```env
# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<anon-or-service-role-key>

# BAC (Behavior Analysis Component) Database
BAC_SUPABASE_URL=https://<bac-project-ref>.supabase.co
BAC_SUPABASE_KEY=<bac-anon-key>

# Configurable Thresholds
MIN_NEW_BEHAVIORS=10

# Azure OpenAI
OPENAI_API_KEY=<azure-api-key>
OPENAI_API_VERSION=2024-02-01
OPENAI_API_BASE=https://<resource-name>.openai.azure.com/
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

---

## 11. How to Run

### Prerequisites
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Setup Database
1. Open the **Supabase SQL Editor** and run `setup_supabase.sql`
2. Populate `.env` with your Supabase and Azure OpenAI credentials

### Generate Test Data
```bash
python generate_test_data.py
```
Creates 3 simulated users (`user_alpha_01`, `user_spartan_02`, `user_chaos_03`) with Azure embeddings seeded into Supabase.

### Run the Pipeline Directly (CLI)
```bash
python pipeline.py --user_id user_alpha_01
python pipeline.py --user_id user_spartan_02
python pipeline.py --user_id user_chaos_03
```

### Start the API Server
```bash
uvicorn api.main:app --host 0.0.0.0 --port 6009 --reload
```
- **Swagger UI:** `http://localhost:6009/docs`
- **ReDoc:** `http://localhost:6009/redoc`
- **Health Check:** `http://localhost:6009/health`

### 6.7 Trigger a Pipeline Run via API
```bash
# 1. Trigger the run (returns job_id immediately)
curl -X POST http://localhost:6009/pipeline/run/user_alpha_01

# 2. Poll for completion
curl http://localhost:6009/pipeline/status/<job_id>

# 3. Get the LLM context prompt
curl http://localhost:6009/context/user_alpha_01
```

### Run Unit Tests
```bash
python -m pytest test_models.py -v
```

---

## 12. Design Decisions & Research Justification

| Decision | Justification |
|----------|---------------|
| **Adaptive DBSCAN** | Mathematically derived epsilon ensures precision; strict semantic capping prevents the merging of distinct habits into generic mega-clusters. |
| **Dual Database Isolation** | CBIE reads from a dedicated read-only BAC repository while maintaining its own writes in a separate profile database, ensuring architectural decoupling. |
| **Batched Inference** | Processing Zero-Shot classification in batches of 32 provides 10x throughput scaling for large behavior histories. |
| **Semantic Suppression** | Cross-similarity checks prevent identity contradictions (e.g., Vegan vs Steak) from contaminating the profile. |
| **t-SNE Embeddings** | Pre-computed 2D projections allow for intuitive visual audit of semantic segmentation in the admin dashboard. |
| **Profile Scoring Radar** | Uses Recharts to visualize the 5 multi-dimensional scoring axes from the AHP Confirmation Model. |
| **Real-time Progress** | Background job polling with stage-specific metadata provides transparency for long-running CPU-bound NLP tasks. |
| **AHP Weight Derivation** | Formal multi-criteria framework providing transparent, justifiable, and reproducible weights. |
| **Zero-Shot NLP Detection** | Understanding synonyms and context dynamically without brittle keyword lists. |
| **Offline batch processing** | Enables comprehensive full-history analysis without real-time latency constraints. |
| **Supabase (PostgreSQL)** | Production-grade vector storage with native similarity search (pgvector). |
