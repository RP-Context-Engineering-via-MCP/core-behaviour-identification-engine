# System Flow and Cluster Naming Documentation

**Generated**: January 6, 2026  
**Core Behavior Identification Engine**

---

## Table of Contents

1. [Complete System Flow](#complete-system-flow)
2. [Detailed Pipeline Phases](#detailed-pipeline-phases)
3. [Cluster Naming System](#cluster-naming-system)
4. [Data Flow Diagram](#data-flow-diagram)
5. [Key Design Principles](#key-design-principles)

---

## Complete System Flow

The Core Behavior Identification Engine processes user interactions through a multi-phase pipeline that transforms raw behavioral observations into verified, clustered preference profiles.

### High-Level Overview

```
User Interaction → Behavior Extraction → Embedding → Storage → 
Clustering → Naming → Classification → Filtering → Profile Generation
```

---

## Detailed Pipeline Phases

### Phase 1: Data Ingestion & Storage

**Location**: Multiple services coordinate this phase

1. **User Interaction Capture**
   - User interacts with the system (asks questions, makes requests)
   - External LLM observes and extracts behavioral signals

2. **Behavior Extraction** (External LLM)
   - Generates `behavior_text`: "prefers visual learning materials"
   - Assigns `credibility`: Quality score (0.0-1.0)
   - Calculates `clarity_score`: How explicit the behavior is
   - Provides `extraction_confidence`: LLM's certainty level

3. **Embedding Generation** 
   - **File**: `src/services/embedding_service.py`
   - **Method**: Uses Azure OpenAI embedding model
   - **Output**: 1536-dimensional vector representation
   - **Purpose**: Enable semantic similarity comparison

4. **Dual Storage Architecture**
   - **Qdrant**: Vector database
     - Stores embeddings + lightweight metadata
     - Source of truth for semantic search
     - Optimized for similarity queries
   - **MongoDB**: Document database
     - Stores full observation documents
     - Stores user prompts and context
     - Supports complex queries and aggregations

---

### Phase 2: Analysis Pipeline

**Entry Point**: `src/services/cluster_analysis_pipeline.py`  
**Method**: `analyze_behaviors_from_storage(user_id: str)`

#### Step 1: Data Retrieval

**File**: `src/services/cluster_analysis_pipeline.py`, line ~54

```python
async def analyze_behaviors_from_storage(self, user_id: str):
    # Fetch behaviors from Qdrant (with embeddings)
    qdrant_behaviors = self.qdrant.get_embeddings_by_user(user_id)
    
    # Fetch prompts from MongoDB for context
    prompts = self.mongodb.get_prompts_by_user(user_id)
    
    # Convert to Observation objects
    observations = self._convert_to_observations(qdrant_behaviors)
```

**Purpose**: Gather all behavioral data for a specific user from both storage systems.

---

#### Step 2: Embedding Preparation

**File**: `src/services/clustering_engine.py`

```python
# Extract embeddings from observations
X = np.array(embeddings)

# L2 normalization (critical for HDBSCAN)
norms = np.linalg.norm(X, axis=1, keepdims=True)
X_normalized = X / (norms + 1e-10)
```

**Why L2 normalization?**
- Makes HDBSCAN work with cosine similarity
- Converts embeddings to unit sphere
- Ensures scale-invariant clustering

---

#### Step 3: HDBSCAN Clustering

**File**: `src/services/clustering_engine.py`, line ~152  
**Method**: `cluster_behaviors()`

**Adaptive Parameter Calculation**:
```python
N = len(observations)

if N < 20:
    # Small datasets: 20% rule
    min_cluster_size = max(3, int(N * 0.20))
else:
    # Larger datasets: Log scaling
    min_cluster_size = max(3, int(math.log(N)))

# Apply user-configured scaling factor
adaptive_min_cluster_size = max(3, int(min_cluster_size * self.size_scaling_factor))
```

**HDBSCAN Configuration**:
```python
clusterer = HDBSCAN(
    min_cluster_size=adaptive_min_cluster_size,
    min_samples=1,  # Single linkage behavior
    cluster_selection_epsilon=0.15,  # Merge threshold
    metric='euclidean',  # On normalized vectors = cosine similarity
    cluster_selection_method='eom'  # Excess of Mass
)

# Perform clustering
cluster_labels = clusterer.fit_predict(X_normalized)

# Extract stability scores from HDBSCAN internals
cluster_stabilities = {}
for cluster_id in set(cluster_labels):
    if cluster_id != -1:  # Exclude noise
        cluster_stabilities[cluster_id] = clusterer.cluster_persistence_[cluster_id]
```

**Output**:
- `cluster_labels`: Array of cluster assignments (e.g., `[0, 0, -1, 1, 0, 2]`)
- `cluster_stabilities`: Dictionary of stability scores (e.g., `{0: 0.85, 1: 0.23, 2: 0.67}`)
- Noise points: Labeled as `-1`

**Key Insight**: Stability scores come directly from HDBSCAN's cluster persistence metric, representing how robust each cluster is to parameter variations.

---

#### Step 4: Build Cluster Objects

**File**: `src/services/cluster_analysis_pipeline.py`, line ~373  
**Method**: `_build_behavior_clusters()`

**Process**:
```python
def _build_behavior_clusters(self, clustering_result, observations, prompts):
    clusters = clustering_result['clusters']  # {cluster_id: [obs_ids]}
    
    for cluster_id, observation_ids in clusters.items():
        if cluster_id == -1:  # Skip noise cluster
            continue
            
        # Get ALL observations in this cluster
        cluster_observations = [
            obs for obs in observations 
            if obs.observation_id in observation_ids
        ]
        
        # Extract all behavior texts (wording variations)
        wording_variations = [obs.behavior_text for obs in cluster_observations]
        
        # Select canonical label (longest/clearest text)
        canonical_label = max(
            wording_variations,
            key=lambda x: (len(x.split()), len(x))
        )
        
        # Calculate Average Behavior Weight (ABW)
        abw = np.mean([obs.credibility * obs.clarity_score 
                       for obs in cluster_observations])
        
        # Calculate recency factor
        timestamps = [obs.timestamp for obs in cluster_observations]
        recency_factor = calculate_recency_weight(timestamps)
        
        # Calculate cluster strength (composite metric)
        # Formula: log(size+1) * ABW * recency / (1 + noise_ratio)
        cluster_strength = (
            math.log(len(cluster_observations) + 1) 
            * abw 
            * recency_factor 
            / (1 + raw_noise_level)
        )
        
        # Get stability from clustering result
        cluster_stability = clustering_result['cluster_stabilities'].get(cluster_id, 0.0)
        
        # Create BehaviorCluster object
        cluster = BehaviorCluster(
            cluster_id=cluster_id,
            observations=cluster_observations,  # ALL member observations
            canonical_label=canonical_label,
            wording_variations=wording_variations,
            cluster_stability=cluster_stability,
            cluster_strength=cluster_strength,
            cluster_size=len(cluster_observations),
            average_behavior_weight=abw,
            tier=TierEnum.SECONDARY  # Default, updated later
        )
        
        behavior_clusters.append(cluster)
    
    return behavior_clusters
```

**Key Metrics**:
- **cluster_strength**: Composite quality metric (size × quality × recency)
- **cluster_stability**: HDBSCAN persistence score (0.0-1.0+)
- **average_behavior_weight**: Mean of (credibility × clarity)

---

#### Step 5: Cluster Naming (LLM-Based)

**File**: `src/services/archetype_service.py`, line ~258  
**Method**: `generate_cluster_name()`

**This is where cluster names are generated!**

**Invocation** (from `cluster_analysis_pipeline.py`, line ~462):
```python
if self.archetype_service:
    try:
        cluster.cluster_name = self.archetype_service.generate_cluster_name(
            wording_variations=cluster.wording_variations,
            cluster_size=cluster.cluster_size,
            tier=cluster.tier.value
        )
    except Exception as e:
        logger.warning(f"Failed to generate cluster name: {e}")
        cluster.cluster_name = cluster.canonical_label  # Fallback
```

**Naming Implementation**:
```python
def generate_cluster_name(self, wording_variations: List[str], 
                         cluster_size: int, tier: str) -> str:
    """Generate a concise descriptive name for a behavior cluster using LLM"""
    
    # Limit to first 5 variations to avoid token overflow
    variations_sample = wording_variations[:5]
    variations_text = "\n".join(f"- {v}" for v in variations_sample)
    
    # Construct LLM prompt
    prompt = f"""Analyze these related user behaviors and create a concise, descriptive name:

{variations_text}

Cluster info:
- Size: {cluster_size} observations
- Importance: {tier}

Requirements:
- 3-6 words maximum
- Capture the CORE pattern across all variations
- Use simple, clear language
- No jargon or marketing speak
- Focus on the behavior, not implementation details

Examples of good names:
- "Visual Learning Preference"
- "Step-by-Step Tutorial Approach"
- "Hands-on Practice Orientation"
- "Detailed Explanation Seeking"

Name:"""

    # Call GPT-4 with low temperature for consistency
    response = self.openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Low temperature ensures consistent naming
        max_tokens=20     # Short output expected
    )
    
    cluster_name = response.choices[0].message.content.strip()
    
    # Clean up common artifacts
    cluster_name = cluster_name.strip('"').strip("'")
    
    return cluster_name
```

**Example Input**:
```python
wording_variations = [
    "prefers Python tutorials with visual diagrams",
    "likes Python code examples with images",
    "wants Python guides with illustrations",
    "prefers Python learning with visual aids"
]
cluster_size = 8
tier = "PRIMARY"
```

**Example Output**:
```
"Visual Python Tutorial Preference"
```

**Key Properties**:
1. **Model**: GPT-4 (high quality, consistent)
2. **Temperature**: 0.3 (low = consistent, deterministic)
3. **Max Tokens**: 20 (enforces brevity)
4. **Input**: Up to 5 representative behavior texts
5. **Output**: 3-6 word descriptive name
6. **Fallback**: Uses `canonical_label` if LLM fails
7. **No Feedback Loop**: Names are presentational only, NOT used in analysis

**Important**: Cluster names do NOT influence clustering, stability, or classification. They are generated AFTER all core analysis is complete.

---

#### Step 6: Epistemic State Assignment

**File**: `src/services/cluster_analysis_pipeline.py`, line ~512  
**Method**: `_assign_epistemic_states()`

**This is the critical classification step that determines which clusters are trustworthy.**

**Process**:
```python
def _assign_epistemic_states(self, behavior_clusters, observations, clustering_result):
    # Calculate global thresholds
    all_stabilities = [c.cluster_stability for c in behavior_clusters]
    all_credibilities = [obs.credibility for obs in observations]
    
    median_stability = np.median(all_stabilities)
    median_credibility = np.median(all_credibilities)
    
    # Absolute minimum threshold for CORE status
    ABSOLUTE_CORE_THRESHOLD = 0.15
    
    for cluster in behavior_clusters:
        stability = cluster.cluster_stability
        
        # Calculate mean credibility of observations in this cluster
        mean_credibility = np.mean([obs.credibility for obs in cluster.observations])
        
        # THREE-STATE CLASSIFICATION:
        
        # 1. CORE: High stability (both relative and absolute thresholds)
        if stability >= median_stability and stability >= ABSOLUTE_CORE_THRESHOLD:
            cluster.epistemic_state = EpistemicState.CORE
            
            # Sub-tier assignment within CORE
            if stability >= np.percentile(all_stabilities, 75):
                cluster.tier = TierEnum.PRIMARY    # Top 25% of stable clusters
            else:
                cluster.tier = TierEnum.SECONDARY  # Middle 50% of stable clusters
                
        # 2. INSUFFICIENT_EVIDENCE: High credibility but unstable cluster
        elif mean_credibility >= median_credibility:
            cluster.epistemic_state = EpistemicState.INSUFFICIENT_EVIDENCE
            cluster.tier = TierEnum.SECONDARY
            
        # 3. NOISE: Low credibility and unstable
        else:
            cluster.epistemic_state = EpistemicState.NOISE
            cluster.tier = TierEnum.NOISE
    
    return behavior_clusters
```

**Classification Logic**:

| Condition | Epistemic State | Tier | Meaning |
|-----------|----------------|------|---------|
| stability ≥ median AND ≥ 0.15 | **CORE** | PRIMARY/SECONDARY | High confidence, expose downstream |
| stability < median BUT high credibility | **INSUFFICIENT_EVIDENCE** | SECONDARY | Needs more data to verify |
| stability < median AND low credibility | **NOISE** | NOISE | Discard from analysis |

**Key Design Decisions**:
- **Dual thresholds**: Must meet both relative (median) and absolute (0.15) thresholds
- **Conservative**: Prefer abstention over false positives
- **Stability = Confidence**: Direct 1:1 mapping from HDBSCAN persistence
- **Preserve insufficient evidence**: Retain for potential future reinforcement

---

#### Step 7: Filter Output

**File**: `src/services/cluster_analysis_pipeline.py`, line ~595

```python
# Keep ONLY CORE clusters for downstream systems
core_clusters = [
    cluster for cluster in behavior_clusters 
    if cluster.epistemic_state == EpistemicState.CORE
]

# Abstention check
if len(core_clusters) == 0:
    logger.info(f"Abstention: No CORE clusters identified for user {user_id}")
    # Return profile with empty behavior_clusters array
```

**Critical Feature**: If NO clusters meet the CORE threshold, the system **abstains** rather than making low-confidence inferences.

---

#### Step 8: Generate Profile

**File**: `src/services/cluster_analysis_pipeline.py`, line ~620

```python
# Create CoreBehaviorProfile
profile = CoreBehaviorProfile(
    user_id=user_id,
    behavior_clusters=core_clusters,  # ONLY CORE clusters
    archetype=archetype_summary,      # Optional user type description
    statistics={
        "total_behaviors_analyzed": len(observations),
        "clusters_formed": num_clusters,
        "core_clusters": len(core_clusters),
        "insufficient_evidence_clusters": num_insufficient,
        "noise_clusters": num_noise,
        "abstention": len(core_clusters) == 0
    },
    timestamp=datetime.now()
)
```

**Output Structure**:
```json
{
  "user_id": "user_665390",
  "behavior_clusters": [
    {
      "cluster_id": 0,
      "cluster_name": "Visual Python Tutorial Preference",
      "canonical_label": "prefers Python tutorials with visual diagrams",
      "wording_variations": ["...", "...", "..."],
      "cluster_stability": 0.87,
      "cluster_strength": 2.45,
      "cluster_size": 8,
      "epistemic_state": "CORE",
      "tier": "PRIMARY",
      "observations": [...]
    }
  ],
  "archetype": "Visual learner focused on Python development",
  "statistics": {
    "total_behaviors_analyzed": 45,
    "clusters_formed": 7,
    "core_clusters": 3,
    "insufficient_evidence_clusters": 2,
    "noise_clusters": 2,
    "abstention": false
  }
}
```

---

### Phase 3: Storage & Response

**Optional**: Store profile in MongoDB for historical tracking

```python
# Store in MongoDB (optional)
if store_profile:
    self.mongodb.store_core_behavior_profile(profile)

# Return via API
return profile
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER INTERACTION                                                 │
│    User: "Show me a Python tutorial with diagrams"                  │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2. BEHAVIOR EXTRACTION (External LLM)                               │
│    behavior_text: "prefers Python tutorials with visuals"           │
│    credibility: 0.87, clarity: 0.92, confidence: 0.85               │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3. EMBEDDING GENERATION                                             │
│    File: src/services/embedding_service.py                          │
│    EmbeddingService → Azure OpenAI                                  │
│    Output: [0.123, -0.456, ..., 0.789] (1536-dim)                  │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4. DUAL STORAGE                                                     │
│    ├─ Qdrant: vector + metadata (semantic search)                  │
│    └─ MongoDB: full observation + prompts (document storage)        │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 5. ANALYSIS TRIGGER                                                 │
│    API: POST /analyze-behaviors-from-storage?user_id=665390         │
│    File: src/api/routes.py                                          │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 6. DATA RETRIEVAL                                                   │
│    File: src/services/cluster_analysis_pipeline.py                  │
│    ClusterAnalysisPipeline.analyze_behaviors_from_storage()         │
│    ├─ Fetch behaviors from Qdrant (with embeddings)                │
│    ├─ Fetch prompts from MongoDB (context)                          │
│    └─ Convert to Observation objects                                │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 7. EMBEDDING PREPARATION                                            │
│    File: src/services/clustering_engine.py                          │
│    ├─ Extract embeddings: X = np.array(embeddings)                 │
│    ├─ L2 normalize: X_norm = X / ||X||                             │
│    └─ Purpose: Enable cosine similarity with HDBSCAN                │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 8. HDBSCAN CLUSTERING                                               │
│    File: src/services/clustering_engine.py (line ~152)              │
│    ├─ Calculate adaptive min_cluster_size:                          │
│    │   • N < 20: 20% rule                                           │
│    │   • N ≥ 20: log(N) scaling                                     │
│    ├─ Run HDBSCAN(min_cluster_size, min_samples=1,                  │
│    │              cluster_selection_epsilon=0.15,                    │
│    │              metric='euclidean', method='eom')                  │
│    ├─ Extract cluster_labels: [0, 0, -1, 1, 0, 2]                  │
│    ├─ Extract stability scores: {0: 0.87, 1: 0.23, 2: 0.67}        │
│    └─ Identify noise: label = -1                                    │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 9. BUILD CLUSTER OBJECTS                                            │
│    File: src/services/cluster_analysis_pipeline.py (line ~373)      │
│    _build_behavior_clusters()                                       │
│    For each cluster:                                                │
│    ├─ Group observations by cluster_id                              │
│    ├─ Extract wording_variations (all behavior texts)               │
│    ├─ Select canonical_label (longest/clearest)                     │
│    ├─ Calculate cluster_strength:                                   │
│    │   log(size+1) * ABW * recency / (1 + noise)                   │
│    ├─ Assign cluster_stability from HDBSCAN                         │
│    └─ Create BehaviorCluster object                                 │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 10. CLUSTER NAMING (LLM-BASED) ⭐                                   │
│     File: src/services/archetype_service.py (line ~258)             │
│     ArchetypeService.generate_cluster_name()                        │
│     ├─ Input: wording_variations (up to 5 samples)                 │
│     ├─ Build prompt with cluster info (size, tier)                 │
│     ├─ Call GPT-4 with temperature=0.3, max_tokens=20              │
│     ├─ Output: "Visual Python Tutorial Preference"                 │
│     └─ Fallback: Use canonical_label if LLM fails                  │
│                                                                      │
│     IMPORTANT: Names are presentational only, NOT used in analysis  │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 11. EPISTEMIC STATE ASSIGNMENT                                      │
│     File: src/services/cluster_analysis_pipeline.py (line ~512)     │
│     _assign_epistemic_states()                                      │
│     ├─ Calculate median_stability across all clusters              │
│     ├─ Calculate median_credibility across all observations        │
│     ├─ For each cluster, classify:                                 │
│     │   • CORE: stability ≥ median AND ≥ 0.15                      │
│     │     └─ Tier: PRIMARY (top 25%) or SECONDARY (middle 50%)     │
│     │   • INSUFFICIENT_EVIDENCE: high cred but unstable            │
│     │   • NOISE: low cred and unstable                             │
│     └─ Update cluster.epistemic_state and cluster.tier             │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 12. FILTER OUTPUT                                                   │
│     File: src/services/cluster_analysis_pipeline.py (line ~595)     │
│     ├─ Keep ONLY clusters where epistemic_state = CORE             │
│     ├─ Discard INSUFFICIENT_EVIDENCE and NOISE from output         │
│     └─ Abstention: If 0 CORE clusters, return empty array          │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 13. GENERATE CORE BEHAVIOR PROFILE                                  │
│     File: src/services/cluster_analysis_pipeline.py (line ~620)     │
│     CoreBehaviorProfile:                                            │
│     ├─ user_id: "user_665390"                                       │
│     ├─ behavior_clusters: [CORE clusters only]                      │
│     ├─ archetype: Optional user type summary                        │
│     ├─ statistics: {total, core, insufficient, noise, abstention}   │
│     └─ timestamp: Current datetime                                  │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 14. STORAGE (Optional)                                              │
│     MongoDB: Store CoreBehaviorProfile document for history         │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 15. API RESPONSE                                                    │
│     File: src/api/routes.py                                         │
│     Return CoreBehaviorProfile JSON to client                       │
│     Status: 200 OK (or 204 No Content if abstention)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Cluster Naming System

### Overview

Cluster naming is a **presentational feature** that makes clusters human-readable. Names are generated **after** all core analysis is complete and do **NOT** influence clustering, stability calculations, or epistemic state assignment.

### Implementation Location

**File**: `src/services/archetype_service.py`  
**Method**: `generate_cluster_name()`, line ~258

### How It Works

1. **Input Collection**:
   ```python
   wording_variations = cluster.wording_variations  # All behavior texts
   cluster_size = len(cluster.observations)
   tier = cluster.tier.value  # PRIMARY, SECONDARY, or NOISE
   ```

2. **Sample Selection** (avoid token overflow):
   ```python
   variations_sample = wording_variations[:5]  # First 5 only
   ```

3. **Prompt Construction**:
   ```python
   prompt = f"""Analyze these related user behaviors and create a concise, descriptive name:

   {variations_text}

   Cluster info:
   - Size: {cluster_size} observations
   - Importance: {tier}

   Requirements:
   - 3-6 words maximum
   - Capture the CORE pattern
   - Use simple, clear language
   - No jargon or marketing speak

   Examples:
   - "Visual Learning Preference"
   - "Step-by-Step Tutorial Approach"
   - "Hands-on Practice Orientation"

   Name:"""
   ```

4. **LLM Call**:
   ```python
   response = self.openai_client.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": prompt}],
       temperature=0.3,  # Low = consistent, deterministic
       max_tokens=20
   )
   cluster_name = response.choices[0].message.content.strip()
   ```

5. **Post-Processing**:
   ```python
   # Remove common artifacts
   cluster_name = cluster_name.strip('"').strip("'")
   ```

6. **Fallback Handling**:
   ```python
   if not cluster_name or cluster_name.strip() == "":
       cluster_name = cluster.canonical_label[:50]
   ```

### Example Flow

**Input**:
```python
wording_variations = [
    "prefers Python tutorials with visual diagrams",
    "likes Python code examples with images",
    "wants Python guides with illustrations",
    "prefers Python learning with visual aids",
    "enjoys Python materials with graphics"
]
cluster_size = 8
tier = "PRIMARY"
```

**LLM Output**:
```
"Visual Python Tutorial Preference"
```

**Alternative Examples**:
- "Step-by-Step Code Guidance"
- "Hands-On Practice Orientation"
- "Detailed Explanation Seeking"
- "Beginner-Friendly Resource Preference"

### Key Properties

| Property | Value | Rationale |
|----------|-------|-----------|
| **Model** | GPT-4 | High quality, consistent output |
| **Temperature** | 0.3 | Low = deterministic, consistent naming |
| **Max Tokens** | 20 | Enforces brevity (3-6 words) |
| **Input Size** | Up to 5 variations | Prevent token overflow |
| **Fallback** | canonical_label | Always have a name |
| **Timing** | After clustering complete | Presentational only |

### When Naming Occurs

**File**: `src/services/cluster_analysis_pipeline.py`, line ~462

```python
# During _build_behavior_clusters()
for cluster in behavior_clusters:
    if self.archetype_service:
        try:
            cluster.cluster_name = self.archetype_service.generate_cluster_name(
                wording_variations=cluster.wording_variations,
                cluster_size=cluster.cluster_size,
                tier=cluster.tier.value
            )
        except Exception as e:
            logger.warning(f"Failed to generate cluster name for {cluster.cluster_id}: {e}")
            cluster.cluster_name = cluster.canonical_label
```

### Important Notes

⚠️ **Naming does NOT affect**:
- Clustering algorithm (HDBSCAN)
- Stability calculations
- Epistemic state classification
- Filtering decisions
- Any downstream analysis

✅ **Naming is used for**:
- UI/UX display
- Human readability
- Debugging/logging
- Report generation

---

## Core Behavior Identification Mechanism

### Overview

The **Core Behavior Identification Mechanism** is the central logic that determines which behavioral clusters represent trustworthy, actionable user preferences. This is a multi-stage process combining clustering quality metrics, statistical thresholds, and conservative inference principles.

### Definition: What is a "Core Behavior"?

A **Core Behavior** is a behavioral pattern that meets ALL of the following criteria:

1. **Statistically Significant**: Forms a density-based cluster (not isolated noise)
2. **Structurally Stable**: High HDBSCAN persistence score (robust to perturbations)
3. **High Quality**: Observations have high credibility and clarity scores
4. **Convergent Evidence**: Multiple observations support the same pattern
5. **Above Absolute Threshold**: Meets minimum stability requirement (≥0.15)
6. **Above Relative Threshold**: Exceeds median stability across all clusters

### Multi-Stage Identification Logic

#### Stage 1: Density-Based Clustering (Pre-Filter)

**File**: `src/services/clustering_engine.py`, line ~152

**Purpose**: Identify natural groupings in behavior embedding space without bias.

**Algorithm**: HDBSCAN (Hierarchical Density-Based Spatial Clustering)

**Process**:
```python
# 1. Normalize embeddings to unit sphere (for cosine similarity)
X_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

# 2. Calculate adaptive min_cluster_size
if N < 20:
    min_cluster_size = max(3, int(N * 0.20))  # 20% for small datasets
else:
    min_cluster_size = max(3, int(math.log(N)))  # log(N) for large datasets

# 3. Run HDBSCAN
clusterer = HDBSCAN(
    min_cluster_size=min_cluster_size,
    min_samples=1,
    cluster_selection_epsilon=0.15,  # Allows clusters within 0.15 distance to merge
    metric='euclidean',  # On normalized vectors = cosine distance
    cluster_selection_method='eom'  # Excess of Mass (prefers stable clusters)
)

cluster_labels = clusterer.fit_predict(X_normalized)
```

**Output**: 
- Cluster assignments for each observation
- Stability scores from `clusterer.cluster_persistence_`
- Noise points labeled as `-1`

**Key Insight**: HDBSCAN automatically identifies noise and only forms clusters where there's genuine density concentration. This is the first filter against spurious patterns.

---

#### Stage 2: Cluster Stability Extraction

**File**: `src/services/clustering_engine.py`, line ~220

**Purpose**: Extract HDBSCAN's internal quality metric for each cluster.

**Mechanism**:
```python
# HDBSCAN's cluster_persistence_ contains stability scores
# Higher scores = more robust clusters that persist across parameter variations
cluster_stabilities = {}
for cluster_id in set(cluster_labels):
    if cluster_id != -1:  # Exclude noise
        cluster_stabilities[cluster_id] = clusterer.cluster_persistence_[cluster_id]
```

**What is Stability?**
- **Mathematical Definition**: The integral of λ (inverse density) over the cluster's lifetime in the HDBSCAN hierarchy
- **Intuitive Meaning**: How long the cluster persists as you vary the density threshold
- **Range**: 0.0 to ∞ (typically 0.0 to 2.0 in practice)
- **Interpretation**:
  - `> 0.5`: Very stable, reliable pattern
  - `0.15 - 0.5`: Moderately stable, needs verification
  - `< 0.15`: Unstable, likely noise or weak signal

**Critical Role**: Stability is the PRIMARY confidence metric in core behavior identification.

---

#### Stage 3: Cluster Quality Metrics Calculation

**File**: `src/services/cluster_analysis_pipeline.py`, line ~373

**Purpose**: Calculate composite quality metrics for each cluster.

**Metrics Computed**:

1. **Average Behavior Weight (ABW)**:
   ```python
   abw = np.mean([obs.credibility * obs.clarity_score 
                  for obs in cluster_observations])
   ```
   - Combines observation-level quality signals
   - Range: 0.0 to 1.0
   - Higher = more trustworthy observations

2. **Recency Factor**:
   ```python
   timestamps = [obs.timestamp for obs in cluster_observations]
   recency_factor = calculate_recency_weight(timestamps)
   ```
   - Exponential decay: recent observations weighted more
   - Accounts for temporal drift in user preferences
   - Range: 0.0 to 1.0

3. **Cluster Strength** (Composite):
   ```python
   cluster_strength = (
       math.log(cluster_size + 1)  # Logarithmic size bonus
       * abw                        # Quality factor
       * recency_factor             # Temporal relevance
       / (1 + noise_ratio)          # Noise penalty
   )
   ```
   - Holistic quality metric
   - Used for ranking and display
   - Not directly used for CORE classification (stability is)

**Key Insight**: Multiple independent metrics provide different quality perspectives, but stability is the gatekeeper for CORE status.

---

#### Stage 4: Epistemic State Classification (CORE IDENTIFICATION)

**File**: `src/services/cluster_analysis_pipeline.py`, line ~512  
**Method**: `_assign_epistemic_states()`

**This is where Core Behaviors are identified!**

**Algorithm**:

```python
def _assign_epistemic_states(self, behavior_clusters, observations, clustering_result):
    # Step 1: Calculate Global Thresholds
    all_stabilities = [c.cluster_stability for c in behavior_clusters]
    all_credibilities = [obs.credibility for obs in observations]
    
    median_stability = np.median(all_stabilities)
    median_credibility = np.median(all_credibilities)
    
    # Step 2: Define Absolute Minimum Threshold
    ABSOLUTE_CORE_THRESHOLD = 0.15  # Empirically validated
    
    # Step 3: Classify Each Cluster
    for cluster in behavior_clusters:
        stability = cluster.cluster_stability
        mean_credibility = np.mean([obs.credibility for obs in cluster.observations])
        
        # DECISION TREE:
        
        # Branch 1: CORE (High Stability)
        if stability >= median_stability and stability >= ABSOLUTE_CORE_THRESHOLD:
            cluster.epistemic_state = EpistemicState.CORE
            
            # Sub-classification within CORE
            if stability >= np.percentile(all_stabilities, 75):
                cluster.tier = TierEnum.PRIMARY     # Top 25% most stable
            else:
                cluster.tier = TierEnum.SECONDARY   # Next 50% stable
        
        # Branch 2: INSUFFICIENT_EVIDENCE (High Credibility but Low Stability)
        elif mean_credibility >= median_credibility:
            cluster.epistemic_state = EpistemicState.INSUFFICIENT_EVIDENCE
            cluster.tier = TierEnum.SECONDARY
            # Retained for potential future upgrade to CORE with more data
        
        # Branch 3: NOISE (Low Credibility and Low Stability)
        else:
            cluster.epistemic_state = EpistemicState.NOISE
            cluster.tier = TierEnum.NOISE
            # Discarded from analysis
    
    return behavior_clusters
```

**Decision Logic Breakdown**:

| Stability vs Median | Stability vs Absolute | Credibility vs Median | Epistemic State | Tier |
|---------------------|----------------------|----------------------|----------------|------|
| ≥ median | ≥ 0.15 | Any | **CORE** | PRIMARY (75th %ile) or SECONDARY |
| < median | Any | ≥ median | INSUFFICIENT_EVIDENCE | SECONDARY |
| < median | Any | < median | NOISE | NOISE |

**Mathematical Formulation**:

$$
\text{CORE} = 
\begin{cases}
\text{True} & \text{if } \sigma \geq \tilde{\sigma} \land \sigma \geq \sigma_{min} \\
\text{False} & \text{otherwise}
\end{cases}
$$

Where:
- $\sigma$ = cluster stability score
- $\tilde{\sigma}$ = median stability across all clusters
- $\sigma_{min}$ = absolute minimum threshold (0.15)

**Why Dual Thresholds?**

1. **Relative Threshold (Median)**:
   - Adapts to data characteristics
   - Ensures top 50% of clusters are considered
   - Prevents over-abstention in high-quality datasets

2. **Absolute Threshold (0.15)**:
   - Prevents false positives in low-quality datasets
   - Empirically validated across diverse user profiles
   - Acts as minimum bar regardless of relative ranking

**Conservative Design**: Both thresholds must be met (AND logic, not OR).

---

#### Stage 5: Core Behavior Filtering

**File**: `src/services/cluster_analysis_pipeline.py`, line ~595

**Purpose**: Extract only CORE clusters for downstream use.

**Process**:
```python
# Filter to CORE only
core_clusters = [
    cluster for cluster in behavior_clusters 
    if cluster.epistemic_state == EpistemicState.CORE
]

# Abstention Check
if len(core_clusters) == 0:
    logger.info(f"Abstention: No CORE clusters for user {user_id}")
    return CoreBehaviorProfile(
        user_id=user_id,
        behavior_clusters=[],  # Empty!
        statistics={
            "total_behaviors_analyzed": len(observations),
            "clusters_formed": len(behavior_clusters),
            "core_clusters": 0,
            "abstention": True
        }
    )

# Success: Return CORE clusters
return CoreBehaviorProfile(
    user_id=user_id,
    behavior_clusters=core_clusters,
    statistics={...}
)
```

**Abstention Mechanism**: 
- If **zero** clusters meet CORE criteria → System abstains
- Returns empty `behavior_clusters` array
- Sets `abstention: true` flag
- **Rationale**: Better to provide no information than misleading information

---

### Complete Core Behavior Identification Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ INPUT: Behavioral Observations (N observations)                     │
│   - behavior_text (semantic content)                                │
│   - embeddings (1536-dim vectors)                                   │
│   - credibility, clarity_score (quality metrics)                    │
│   - timestamps (temporal information)                               │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Density-Based Clustering (HDBSCAN)                         │
│   ├─ Normalize embeddings (L2 norm)                                │
│   ├─ Adaptive min_cluster_size: log(N) or 20% rule                 │
│   ├─ Run HDBSCAN with EOM cluster selection                        │
│   └─ Output: {cluster_labels, noise_points, persistence_scores}     │
│                                                                      │
│   FILTER: Noise points (-1 label) excluded immediately              │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Cluster Stability Extraction                               │
│   ├─ Extract cluster_persistence_ from HDBSCAN                     │
│   ├─ Map cluster_id → stability_score                              │
│   └─ Output: {cluster_stabilities}                                  │
│                                                                      │
│   PRIMARY CONFIDENCE METRIC established                             │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Cluster Quality Metrics                                    │
│   For each cluster:                                                 │
│   ├─ ABW = mean(credibility × clarity_score)                       │
│   ├─ recency_factor = exp_decay(timestamps)                        │
│   ├─ cluster_strength = log(size) × ABW × recency / (1+noise)     │
│   └─ Output: Enriched cluster objects                               │
│                                                                      │
│   SUPPLEMENTARY METRICS calculated                                  │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Epistemic State Classification ⭐ CORE IDENTIFICATION     │
│   Calculate thresholds:                                             │
│   ├─ median_stability = median(all stabilities)                    │
│   ├─ median_credibility = median(all credibilities)                │
│   └─ ABSOLUTE_CORE_THRESHOLD = 0.15                                 │
│                                                                      │
│   For each cluster, apply DECISION TREE:                            │
│                                                                      │
│   IF stability ≥ median_stability AND stability ≥ 0.15:            │
│      → CORE (High confidence, expose downstream)                   │
│      → Tier: PRIMARY (top 25%) or SECONDARY (next 50%)             │
│                                                                      │
│   ELIF mean_credibility ≥ median_credibility:                      │
│      → INSUFFICIENT_EVIDENCE (Retain for reinforcement)            │
│      → Tier: SECONDARY                                              │
│                                                                      │
│   ELSE:                                                              │
│      → NOISE (Discard)                                              │
│      → Tier: NOISE                                                  │
│                                                                      │
│   CORE BEHAVIORS IDENTIFIED at this stage                           │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Core Behavior Filtering                                    │
│   ├─ Extract: core_clusters = [c for c if c.state == CORE]        │
│   ├─ Count: num_core = len(core_clusters)                          │
│   └─ Abstention check: if num_core == 0 → return empty             │
│                                                                      │
│   FINAL OUTPUT determined                                           │
└────────────────────┬────────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ OUTPUT: Core Behavior Profile                                       │
│   ├─ behavior_clusters: [CORE clusters only]                        │
│   ├─ statistics: {total, core, insufficient, noise, abstention}     │
│   └─ Downstream systems consume CORE behaviors with confidence      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Example Scenarios

#### Scenario 1: Clear Core Behaviors

**Input**: 45 observations, 7 clusters formed

| Cluster | Stability | Median Stability | Absolute Min | Credibility | Classification |
|---------|-----------|-----------------|--------------|-------------|----------------|
| 0 | 0.87 | 0.34 | 0.15 | 0.92 | **CORE (PRIMARY)** ✓ |
| 1 | 0.65 | 0.34 | 0.15 | 0.88 | **CORE (PRIMARY)** ✓ |
| 2 | 0.41 | 0.34 | 0.15 | 0.85 | **CORE (SECONDARY)** ✓ |
| 3 | 0.28 | 0.34 | 0.15 | 0.78 | INSUFFICIENT |
| 4 | 0.19 | 0.34 | 0.15 | 0.45 | INSUFFICIENT |
| 5 | 0.08 | 0.34 | 0.15 | 0.62 | INSUFFICIENT |
| 6 | 0.03 | 0.34 | 0.15 | 0.21 | NOISE |

**Result**: 3 CORE clusters identified → Return profile with 3 behaviors

---

#### Scenario 2: Abstention (No Core Behaviors)

**Input**: 12 observations, 4 clusters formed

| Cluster | Stability | Median Stability | Absolute Min | Credibility | Classification |
|---------|-----------|-----------------|--------------|-------------|----------------|
| 0 | 0.12 | 0.09 | 0.15 | 0.75 | INSUFFICIENT (fails absolute) |
| 1 | 0.09 | 0.09 | 0.15 | 0.68 | INSUFFICIENT (fails absolute) |
| 2 | 0.08 | 0.09 | 0.15 | 0.55 | NOISE |
| 3 | 0.05 | 0.09 | 0.15 | 0.42 | NOISE |

**Result**: 0 CORE clusters → **Abstention** → Return empty behavior_clusters

**Reasoning**: All clusters fail absolute threshold (< 0.15), even though some meet relative threshold. System conservatively abstains.

---

#### Scenario 3: Borderline Case

**Input**: 8 observations, 2 clusters formed

| Cluster | Stability | Median Stability | Absolute Min | Credibility | Classification |
|---------|-----------|-----------------|--------------|-------------|----------------|
| 0 | 0.18 | 0.145 | 0.15 | 0.82 | **CORE (PRIMARY)** ✓ |
| 1 | 0.11 | 0.145 | 0.15 | 0.79 | INSUFFICIENT (fails absolute) |

**Result**: 1 CORE cluster identified → Return profile with 1 behavior

**Reasoning**: Cluster 0 meets both thresholds (0.18 ≥ 0.145 AND 0.18 ≥ 0.15). Cluster 1 fails absolute threshold despite high credibility.

---

### Why This Mechanism Works

**1. Multi-Stage Filtering Cascade**
- Each stage applies independent quality checks
- Failures at any stage prevent CORE classification
- Reduces false positive rate dramatically

**2. Data-Adaptive Thresholds**
- Median stability adapts to dataset characteristics
- Absolute threshold prevents over-adaptation
- Works across diverse user profiles (sparse to dense)

**3. Conservative by Design**
- AND logic (not OR) for dual thresholds
- Abstention over low-confidence inference
- Explicit uncertainty states (INSUFFICIENT_EVIDENCE)

**4. Leverages Domain-Appropriate Algorithm**
- HDBSCAN naturally handles variable density
- Stability score is well-studied metric
- No arbitrary hyperparameter tuning needed

**5. Transparent Decision Boundaries**
- Clear mathematical criteria
- Debuggable and auditable
- Can explain why any cluster is/isn't CORE

---

### Validation and Tuning

**Absolute Threshold (0.15) Validation**:

The 0.15 threshold was empirically validated across:
- 6 diverse user profiles (sparse to massive datasets)
- Manual expert review of cluster quality
- Precision-recall tradeoff analysis

**Results** (from `docs/EVALUATION_COMPLETE.md`):
- **Precision**: 0.89 (89% of CORE clusters verified as accurate)
- **Recall**: 0.82 (captures most meaningful behaviors)
- **F1 Score**: 0.85 (balanced performance)

**Threshold Sensitivity** (from `src/evaluation/threshold_sensitivity_analysis.py`):
- Tested thresholds: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30
- **Optimal**: 0.15 (best F1 score, acceptable abstention rate)
- Too low (< 0.10): False positives increase
- Too high (> 0.20): Abstention rate > 30% (over-conservative)

---

### Code Reference Summary

| Stage | File | Method/Lines | Purpose |
|-------|------|--------------|---------|
| Stage 1 | `clustering_engine.py` | `cluster_behaviors()`, ~152 | HDBSCAN clustering |
| Stage 2 | `clustering_engine.py` | ~220 | Stability extraction |
| Stage 3 | `cluster_analysis_pipeline.py` | `_build_behavior_clusters()`, ~373 | Quality metrics |
| Stage 4 | `cluster_analysis_pipeline.py` | `_assign_epistemic_states()`, ~512 | CORE identification |
| Stage 5 | `cluster_analysis_pipeline.py` | ~595 | Filtering & abstention |

---

## Key Design Principles

### 1. Clusters Are Primary Entities

Individual behavioral observations are **signals** that are aggregated into **clusters**. The system reasons about user preferences at the cluster level, not at the individual observation level.

**Rationale**: Reduces noise, increases confidence through convergent evidence.

---

### 2. Density-First Approach

Clustering happens **before** any threshold filtering. HDBSCAN identifies natural density-based groupings in the embedding space without preconceived notions of "good" vs "bad" clusters.

**Rationale**: Let the data structure emerge naturally, then apply epistemic judgment.

---

### 3. Conservative Inference

The system prefers **abstention** over false positives. If no clusters meet the CORE stability threshold, the system returns an empty profile rather than making low-confidence inferences.

**Code**:
```python
if len(core_clusters) == 0:
    return CoreBehaviorProfile(
        user_id=user_id,
        behavior_clusters=[],  # Empty!
        statistics={"abstention": True}
    )
```

**Rationale**: Trust is paramount. Better to say "I don't know" than to mislead.

---

### 4. Three-State Classification

Every cluster is classified into exactly one epistemic state:

| State | Meaning | Downstream Use |
|-------|---------|----------------|
| **CORE** | High confidence, stable | Exposed to applications |
| **INSUFFICIENT_EVIDENCE** | Promising but unverified | Retained for future reinforcement |
| **NOISE** | Low quality | Discarded |

**Rationale**: Clear decision boundaries, explicit uncertainty handling.

---

### 5. Stability = Confidence

Cluster stability (from HDBSCAN's persistence score) is the **primary confidence metric**. It represents how robust a cluster is to parameter variations and data perturbations.

**Mapping**:
```
High stability → High confidence → CORE state
Low stability → Low confidence → INSUFFICIENT or NOISE state
```

**Rationale**: Leverage HDBSCAN's built-in quality metric rather than inventing new heuristics.

---

### 6. Naming Is Presentational Only

LLM-generated cluster names are **not** used in any analysis logic. They are created after all decisions are finalized.

**Rationale**: Prevent naming artifacts from influencing scientific inference. Names are for humans, not algorithms.

---

### 7. Dual Storage Architecture

- **Qdrant**: Optimized for vector similarity search
- **MongoDB**: Optimized for complex document queries

**Rationale**: Use the right tool for each job. Vectors in vector DB, documents in document DB.

---

### 8. Adaptive Parameter Scaling

Clustering parameters (e.g., `min_cluster_size`) adapt based on dataset size:
- Small datasets (N < 20): 20% rule
- Large datasets (N ≥ 20): Logarithmic scaling

**Rationale**: Avoid overfitting small datasets, avoid underfitting large datasets.

---

### 9. Multi-Dimensional Quality Metrics

Cluster quality is assessed through multiple independent metrics:
- **Stability**: HDBSCAN persistence
- **Strength**: Size × Quality × Recency
- **Credibility**: Mean observation credibility
- **Epistemic State**: Final classification

**Rationale**: No single metric captures all aspects of cluster quality.

---

### 10. Temporal Awareness

Recent behaviors are weighted more heavily through recency factors.

**Code**:
```python
recency_factor = calculate_recency_weight(timestamps)
cluster_strength *= recency_factor
```

**Rationale**: User preferences evolve. Recent evidence is more predictive.

---

## File Reference Summary

| Component | File | Key Lines |
|-----------|------|-----------|
| Data Retrieval | `src/services/cluster_analysis_pipeline.py` | ~54 |
| Embedding Prep | `src/services/clustering_engine.py` | ~110 |
| HDBSCAN Clustering | `src/services/clustering_engine.py` | ~152 |
| Cluster Building | `src/services/cluster_analysis_pipeline.py` | ~373 |
| Cluster Naming | `src/services/archetype_service.py` | ~258 |
| Epistemic States | `src/services/cluster_analysis_pipeline.py` | ~512 |
| Output Filtering | `src/services/cluster_analysis_pipeline.py` | ~595 |
| Profile Generation | `src/services/cluster_analysis_pipeline.py` | ~620 |
| API Routes | `src/api/routes.py` | Multiple |
| Data Models | `src/models/schemas.py` | Full file |

---

## Conclusion

The Core Behavior Identification Engine uses a sophisticated pipeline that:

1. **Collects** behavioral observations with embeddings
2. **Clusters** them using density-based methods (HDBSCAN)
3. **Assesses** cluster quality via stability and credibility
4. **Names** clusters using LLM for human readability
5. **Classifies** clusters into epistemic states (CORE/INSUFFICIENT/NOISE)
6. **Filters** to only high-confidence CORE clusters
7. **Outputs** verified preference profiles or abstains when uncertain

The cluster naming system specifically uses **GPT-4** with **low temperature (0.3)** to generate **3-6 word descriptive names** based on representative behavior texts. These names are generated **after** all analysis is complete and serve a **presentational purpose only**.

---

**Document Version**: 1.0  
**Last Updated**: January 6, 2026  
**Maintainer**: Core Behavior Identification Engine Team
