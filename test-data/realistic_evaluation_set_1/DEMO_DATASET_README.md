# Demo Dataset: `user_demo_epistemic`

## Purpose

This controlled dataset demonstrates the Core Behavior Identification Engine's ability to **conservatively identify stable behavioral patterns** and classify them into three epistemic states:

1. **CORE** - Clearly stable, high-confidence behaviors
2. **INSUFFICIENT_EVIDENCE** - Promising patterns with insufficient support
3. **NOISE** - Low-quality, single-occurrence signals

## Dataset Composition

### Overview
- **User ID**: `user_demo_epistemic`
- **Total Behaviors**: 19 behaviors
- **Total Prompts**: 39 prompts
- **Time Span**: 14 days (2 weeks)
- **Time Distribution**:
  - Days 1-3: Exploratory phase (noise-heavy)
  - Days 4-10: Stable behavior phase (repeated patterns)
  - Days 11-14: Drift phase (some noise, some reinforcement)

---

## Expected Epistemic States

### 🟢 CORE Behaviors (2 behaviors)

#### 1. Visual Python Explanations
- **Behavior**: "prefers visual explanations for Python concepts"
- **Occurrences**: 8 prompts
- **Credibility**: 0.82-0.94 (avg: 0.88)
- **Clarity**: 0.89
- **Time Distribution**: 70% Days 4-10, 30% Days 11-14

**Sample Prompts** (wording variations):
```
- "I'd like a visual breakdown of Python generators in Python"
- "Can you show me a diagram explaining Python descriptors?"
- "Could you illustrate Python decorators with a chart?"
- "I prefer seeing Python generators as a diagram"
- "Show me a flowchart for Python context managers"
```

**Why CORE?**
- ✅ High occurrence count (8)
- ✅ Spread across multiple days
- ✅ High credibility (0.82-0.94)
- ✅ Clear semantic consistency
- ✅ Should form stable HDBSCAN cluster

---

#### 2. Debugging Focus
- **Behavior**: "focuses on debugging and error resolution"
- **Occurrences**: 9 prompts
- **Credibility**: 0.78-0.92 (avg: 0.85)
- **Clarity**: 0.94
- **Time Distribution**: 70% Days 4-10, 30% Days 11-14

**Sample Prompts** (wording variations):
```
- "Debug my type errors implementation"
- "Troubleshooting database connections problems"
- "Fix my broken import errors code"
- "Resolve async functions issue"
- "Help me troubleshoot API calls"
- "Error handling for race conditions"
```

**Why CORE?**
- ✅ Highest occurrence count (9)
- ✅ Distributed temporally
- ✅ High credibility (0.78-0.92)
- ✅ Clear action pattern (debugging verbs)
- ✅ Should form very stable cluster

---

### 🟡 INSUFFICIENT_EVIDENCE Behaviors (2 behaviors)

#### 3. System Design Interest
- **Behavior**: "interested in system design patterns"
- **Occurrences**: 4 prompts
- **Credibility**: 0.68-0.83 (avg: 0.76)
- **Clarity**: 0.72
- **Time Distribution**: Sparse across Days 4-14

**Sample Prompts**:
```
- "Tell me about circuit breakers in distributed systems"
- "How does caching strategies work in microservices?"
- "System design for load balancing"
- "Explain event sourcing architecture pattern"
```

**Why INSUFFICIENT_EVIDENCE?**
- ⚠️ Low occurrence count (4) - below stability threshold
- ⚠️ Sparse temporal distribution
- ✅ High credibility (0.68-0.83) - signals quality
- ❌ Likely fails HDBSCAN stability threshold (< 0.15)
- 📌 **Expected State**: INSUFFICIENT_EVIDENCE

---

#### 4. Security Awareness
- **Behavior**: "asks about security best practices"
- **Occurrences**: 3 prompts
- **Credibility**: 0.70-0.85 (avg: 0.77)
- **Clarity**: 0.74
- **Time Distribution**: Sparse across Days 4-14

**Sample Prompts**:
```
- "What are security considerations for API authentication?"
- "How to secure JWT tokens?"
- "Best practices for SQL injection prevention security"
```

**Why INSUFFICIENT_EVIDENCE?**
- ⚠️ Very low occurrence count (3)
- ⚠️ Sparse temporal distribution
- ✅ Decent credibility (0.70-0.85)
- ❌ Will fail stability threshold
- 📌 **Expected State**: INSUFFICIENT_EVIDENCE

---

### 🔴 NOISE Behaviors (15 behaviors)

**Characteristics**:
- **Occurrences**: 1 prompt each (single mentions)
- **Credibility**: 0.29-0.52 (low range)
- **Clarity**: 0.40-0.65 (moderate to low)
- **Time Distribution**: 60% in Days 1-3 (exploratory), 40% in Days 11-14 (drift)

**Examples**:
```
- "What's the latest score in football?" (credibility: 0.35)
- "What's the weather today?" (credibility: 0.42)
- "How does blockchain work?" (credibility: 0.51)
- "Recipe for chocolate cake?" (credibility: 0.38)
- "Recommend a good movie" (credibility: 0.45)
- "What's the square root of 144?" (credibility: 0.52)
- "Best time to visit Japan?" (credibility: 0.37)
```

**Why NOISE?**
- ❌ Single occurrence (no reinforcement)
- ❌ Low credibility (0.29-0.52)
- ❌ Semantically diverse (no clustering)
- ❌ Will be labeled as HDBSCAN noise (-1)
- 📌 **Expected State**: NOISE

---

## Expected Clustering Results

### Predicted Cluster Formation

| Cluster ID | Behavior | Size | Expected Stability | Expected State |
|------------|----------|------|-------------------|----------------|
| 0 | Visual Python Explanations | 8 | > 0.50 | **CORE (PRIMARY)** |
| 1 | Debugging Focus | 9 | > 0.50 | **CORE (PRIMARY)** |
| 2 | System Design | 4 | 0.10-0.14 | INSUFFICIENT_EVIDENCE |
| 3 | Security | 3 | 0.08-0.12 | INSUFFICIENT_EVIDENCE |
| -1 | Noise | 15 | N/A | NOISE |

---

## Key Testing Objectives

### ✅ What This Dataset SHOULD Demonstrate

1. **Conservative Inference**:
   - System identifies 2 CORE behaviors (not all 19)
   - System abstains from promoting weak signals

2. **Dual Threshold Logic**:
   - Clusters 0, 1: Pass both median AND absolute thresholds
   - Clusters 2, 3: Fail absolute threshold despite decent credibility
   - Noise: Labeled -1 by HDBSCAN

3. **Three-State Classification**:
   - CORE: Expose to downstream (2 clusters)
   - INSUFFICIENT_EVIDENCE: Retain for future (2 clusters)
   - NOISE: Discard (15 behaviors)

4. **Semantic Robustness**:
   - CORE clusters demonstrate wording variation tolerance
   - Embeddings should cluster semantically similar prompts

5. **Temporal Awareness**:
   - Recent occurrences in Days 11-14 show behavior persistence
   - Recency weighting factors into cluster strength

---

## Usage

### Load Dataset

```python
import json

# Load behaviors
with open('behaviors_user_demo_epistemic.json') as f:
    behaviors = json.load(f)

# Load prompts
with open('prompts_user_demo_epistemic.json') as f:
    prompts = json.load(f)

print(f"Total behaviors: {len(behaviors)}")
print(f"Total prompts: {len(prompts)}")
```

### Expected API Response

```json
{
  "user_id": "user_demo_epistemic",
  "behavior_clusters": [
    {
      "cluster_id": 0,
      "cluster_name": "Visual Python Learning",
      "cluster_size": 8,
      "cluster_stability": 0.67,
      "epistemic_state": "CORE",
      "tier": "PRIMARY"
    },
    {
      "cluster_id": 1,
      "cluster_name": "Debugging and Troubleshooting",
      "cluster_size": 9,
      "cluster_stability": 0.72,
      "epistemic_state": "CORE",
      "tier": "PRIMARY"
    }
  ],
  "statistics": {
    "total_behaviors_analyzed": 19,
    "clusters_formed": 4,
    "core_clusters": 2,
    "insufficient_evidence_clusters": 2,
    "noise_clusters": 0,
    "abstention": false
  }
}
```

---

## Validation Checklist

After running analysis on this dataset, verify:

- [ ] **2 CORE clusters identified** (not 4, not 19)
- [ ] **Cluster 0**: Visual Python (size ≈ 8, stability > 0.5)
- [ ] **Cluster 1**: Debugging (size ≈ 9, stability > 0.5)
- [ ] **2 INSUFFICIENT_EVIDENCE clusters** (system design, security)
- [ ] **15 NOISE behaviors** (single occurrences, low credibility)
- [ ] **No false positives**: Sparse behaviors NOT promoted to CORE
- [ ] **Cluster names** are semantically meaningful
- [ ] **Abstention = false** (at least 2 CORE clusters exist)

---

## Success Criteria

This dataset successfully demonstrates the claim:

> **"Given multiple behavioral hypotheses over time, the system can conservatively identify which ones are truly stable."**

**Evidence**:
1. ✅ Not all behaviors promoted (19 → 2 CORE)
2. ✅ Dual thresholds enforced (median + absolute)
3. ✅ Three-state classification visible
4. ✅ Sparse signals correctly rejected
5. ✅ Stable patterns correctly identified

---

## Files

- `behaviors_user_demo_epistemic.json` - 19 behavior observations
- `prompts_user_demo_epistemic.json` - 39 user prompts
- `dataset_summary.json` - Overall summary
- `DEMO_DATASET_README.md` - This file

---

**Generated**: January 6, 2026  
**Author**: Core Behavior Identification Engine Team  
**Purpose**: Demonstration of conservative epistemic state classification
