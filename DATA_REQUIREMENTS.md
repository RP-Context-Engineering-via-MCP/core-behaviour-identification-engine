# CBIE Engine — How Behaviors Are Identified & Data Requirements

## Pipeline Overview

The CBIE engine processes raw user behaviors through a **three-stage pipeline** to identify stable, long-term core interests:

```
Raw Behaviors → [Stage 1: Topic Discovery] → [Stage 2: Temporal Analysis] → [Stage 3: Confirmation Model] → Core Behaviour Profile
```

---

## Stage 1: Topic Discovery & Fact Isolation

### 1a. Fact Isolation (Zero-Shot Classification)

Every behavior is scored by the **BART zero-shot classifier** (`facebook/bart-large-mnli`) against six conceptual labels:

| Label | Purpose |
|---|---|
| `medical condition or severe allergy` | Detect health constraints |
| `strict dietary restriction` | Detect dietary constraints |
| `hobby or regular habit` | Identify standard behaviors |
| `personal preference` | Identify preferences |
| `informational query` | Detect informational intent |
| `random trivia or one-off query` | Detect noise/throwaway queries |

**Fact classification logic:**
- Base confidence = `max(medical_score, dietary_score)` from zero-shot
- If BAC `intent == "CONSTRAINT"` → +0.10 boost
- If `polarity == "NEGATIVE"` AND `intent == "CONSTRAINT"` → +0.05 boost
- **Threshold: combined confidence ≥ 0.70 → classified as Absolute Fact**

Facts are automatically assigned `status: "Stable Fact"` and skip the confirmation model scoring entirely.

### 1b. Entity Extraction

Uses **spaCy** NER with a custom **EntityRuler** for domain-specific terms (e.g., `kubernetes`, `docker`, `dbscan`, `hdbscan`). Extracted entities enrich the behavior metadata.

### 1c. Embedding Generation

Each behavior's `source_text` is vectorized using **`all-MiniLM-L6-v2`** (384-dimensional sentence embeddings). Pre-computed embeddings from the database are reused; missing ones are generated on the fly.

### 1d. DBSCAN Clustering

Behaviors are grouped into latent topic clusters using **DBSCAN** with:

- **Adaptive epsilon**: Calculated via the **k-distance graph** (KneeLocator). Clamped to `[0.20, 0.75]`.
- **min_samples = 2**: A cluster needs at least 2 semantically similar behaviors.
- **Polarity Penalty**: POSITIVE ↔ NEGATIVE behavior pairs receive a distance of 1000, preventing them from clustering together even if semantically similar.

Behaviors that don't fit any cluster are labeled as **noise** (`cluster_id = -1`) and excluded from the final profile.

Each surviving cluster is then labeled by **GPT-4o-mini**, which reads the raw behavior texts and generates a 3–5 word generalized topic name (e.g., "Python Backend Development").

---

## Stage 2: Temporal Analysis

For each cluster, two temporal metrics are computed from the behavior timestamps:

### Consistency Score (Gini Coefficient)

Measures how **regular/uniform** the time intervals between behaviors are.

- Computes inter-event times (in days) between consecutive behaviors
- Calculates the **Gini coefficient** of those intervals
- **0.0** = perfectly consistent (equal spacing) → strong habit signal
- **1.0** = highly inconsistent (bursty/irregular) → weak habit signal
- Requires **≥ 2 events** (otherwise returns 1.0 = "cannot determine")

### Trend Score (Mann-Kendall Test)

Detects whether a metric (e.g., `clarity_score`) is **statistically increasing or decreasing** over time.

- **+1.0** = significant upward trend (growing engagement)
- **-1.0** = significant downward trend (fading interest)
- **0.0** = no significant trend
- Uses α = 0.10 significance level
- Requires **≥ 4 data points** (otherwise returns 0.0 = "no trend")

---

## Stage 3: Confirmation Model (AHP-Weighted Heuristic)

Combines all signals into a final **core score** using weights derived from the Analytic Hierarchy Process (AHP):

| Factor | Weight | Source | Normalization |
|---|---|---|---|
| **Consistency** | 0.35 | Gini coefficient | `1.0 - gini` (higher = more consistent = better) |
| **Credibility** | 0.30 | BAC metadata | Raw value (0.0–1.0) |
| **Frequency** | 0.25 | Behavior count | `freq / max_freq` (relative to largest cluster) |
| **Trend** | 0.10 | Mann-Kendall result | `(trend + 1) / 2` (maps -1…+1 to 0…1) |

### Status Classification

| Core Score | Status | Meaning |
|---|---|---|
| ≥ 0.70 | **Stable** | Confirmed long-term core interest |
| ≥ 0.40 | **Emerging** | Growing interest, needs more data |
| ≥ 0.15 | **Noise** | Not significant enough to confirm |
| < 0.15 | **ARCHIVED_CORE** | Previously relevant, now faded |
| (any, if fact) | **Stable Fact** | Permanent identity constraint |

---

## Pipeline Filters (Post-Confirmation)

### Contradiction Suppression
If a cluster has **cosine similarity < 0.1** to fact embeddings AND **>50% NEGATIVE polarity** behaviors → status is overridden to `"CONTRADICTED"` and excluded. This prevents adversarial behaviors (e.g., "eating peanuts" when the user has a nut allergy) from being confirmed.

### Trivia Noise Filter
If a cluster has **avg classifier_trivia > 0.8** AND **avg clarity_score < 0.65** → status is overridden to `"Noise"`. This catches low-value one-off queries that happen to cluster together.

---

## Minimum Data Requirements

### Per User (Overall)

| Requirement | Minimum | Recommended | Source |
|---|---|---|---|
| Total behaviors (full run) | ≥ 1 | 50+ | `pipeline.py` — returns empty if 0 |
| Total behaviors (incremental run) | ≥ 10 new | 20+ new | `pipeline.py:93` — `MIN_NEW_BEHAVIORS = 10` |
| Fetch limit per run | — | Up to 500 | `data_adapter.py:109` |
| t-SNE visualization | ≥ 4 embeddable | 20+ | `pipeline.py:309` |

### Per Cluster (For Meaningful Analysis)

| Requirement | Minimum | Recommended | Reason |
|---|---|---|---|
| Behaviors to form a cluster | 2 | 4+ | DBSCAN `min_samples=2` |
| Behaviors for consistency score | 2 | 5+ | Gini needs ≥2 inter-event intervals |
| Behaviors for trend detection | 4 | 6+ | Mann-Kendall needs ≥4 data points |
| Behaviors for adaptive epsilon | 4 | 10+ | k-distance graph needs >k+1 points |

### Temporal Span

| Scenario | Minimum Span | Recommended Span | Reason |
|---|---|---|---|
| Stable interest detection | 2+ weeks | 60–120 days | Gini needs multiple intervals to measure regularity |
| Emerging interest detection | 3+ days | 5–12 day burst | Recent concentration signals growing interest |
| Archived/decayed interest | 30+ days old | 100–200 days old | Old timestamps with no recent activity |
| Consistent habit signal | Evenly spaced | Every 1–3 days over 30+ days | Low Gini (< 0.2) requires uniform spacing |

### Required Fields per Behavior Record

| Field | Required | Type | Notes |
|---|---|---|---|
| `behavior_id` | ✅ | UUID string | Unique identifier |
| `user_id` | ✅ | string | User identifier |
| `behavior_text` | ✅ | string | Natural language behavior statement |
| `created_at` | ✅ | bigint (epoch-ms) | Timestamp for temporal analysis |
| `behavior_state` | ✅ | string | Must be `"ACTIVE"` to be fetched |
| `embedding` | Recommended | vector(384) | Pre-computed `all-MiniLM-L6-v2` embedding |
| `intent` | Recommended | string | `CONSTRAINT`, `ACTION`, `EXPLORATION`, `QUERY`, etc. |
| `polarity` | Recommended | string | `POSITIVE`, `NEGATIVE`, `NEUTRAL` |
| `credibility` | Recommended | float (0–1) | Affects confirmation score (weight 0.30) |
| `clarity_score` | Recommended | float (0–1) | Used for Mann-Kendall trend detection |
| `extraction_confidence` | Optional | float (0–1) | Logged but not directly used in scoring |
| `target` | Optional | string | Free-text subject metadata |
| `context` | Optional | string | Domain context (e.g., `technology`, `health`) |
| `session_id` | Required by BAC DB | UUID string | NOT NULL constraint in BAC database |

### Behavior Text Quality

For the pipeline to produce meaningful results, behavior texts should:

- **Start with intent-style phrasing**: e.g., "likes", "prefers", "avoids", "practices", "researching"
- **Clearly mention a subject/topic**: e.g., "Python backend development", "dividend stocks"
- **Be semantically consistent within a topic**: Paraphrased variations of the same interest should produce embeddings close enough to cluster together (cosine similarity > 0.75)
- **Be semantically distinct across topics**: Different interests should produce embeddings far enough apart to form separate clusters

---

## Output: Core Behaviour Profile

The final output is a JSON profile containing:

```json
{
  "user_id": "example_user",
  "total_raw_behaviors": 80,
  "confirmed_interests": [
    {
      "cluster_id": "fact_0",
      "label": "Severe Nut Allergy",
      "representative_topics": ["diagnosed with severe tree nut allergy"],
      "frequency": 5,
      "consistency_score": 1.0,
      "trend_score": 0.0,
      "core_score": 1.0,
      "status": "Stable Fact"
    },
    {
      "cluster_id": 0,
      "representative_topics": ["Python Backend Development"],
      "frequency": 25,
      "consistency_score": 0.05,
      "trend_score": 0.0,
      "core_score": 0.82,
      "avg_credibility": 0.89,
      "status": "Stable"
    }
  ],
  "embedding_map": [ ... ],
  "identity_anchor_prompt": "--- SYSTEM IDENTITY ANCHOR FOR USER: example_user ---\n..."
}
```

The `identity_anchor_prompt` is a ready-to-inject system prompt string that summarizes the user's core traits for LLM personalization, categorized into Critical Constraints, Verified Stable Preferences, Emerging Interests, and Archived Outdated Habits.
