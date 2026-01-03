# Evaluation Plan: Baseline Comparison and Multi-User Validation

**Date:** January 3, 2026  
**Purpose:** Research validation for Bachelor's thesis  
**Status:** Planning Phase

---

## Evaluation Question

**Does a conservative, stability-gated classification system reduce false-positive preference exposure compared to frequency-based methods under sparse data conditions (N<20)?**

---

## 1. Baseline Method: Frequency-Only Preference Detection

### Algorithm

**Naive Frequency-Based Classification** (deliberately simple to show contrast)

```python
def frequency_baseline_classify(behaviors: List[Behavior]) -> List[Classification]:
    """
    Classify behaviors based solely on reinforcement frequency.
    No clustering, no stability checks - just count occurrences.
    """
    classifications = []
    
    for behavior in behaviors:
        # Count total reinforcements across all prompts
        total_reinforcements = sum(p.reinforcement_count for p in behavior.prompts)
        
        # Simple threshold: behaviors with >= 5 reinforcements are "CORE"
        if total_reinforcements >= 5:
            status = "CORE"
            confidence = min(1.0, total_reinforcements / 50)  # Cap at 50
        elif total_reinforcements >= 2:
            status = "SECONDARY"
            confidence = total_reinforcements / 10
        else:
            status = "NOISE"
            confidence = 0.1
        
        classifications.append({
            "behavior": behavior.description,
            "status": status,
            "reinforcements": total_reinforcements,
            "confidence": confidence
        })
    
    return classifications
```

### Why This Baseline?

1. **Represents naive approach**: What users would naturally do (count occurrences)
2. **No false-positive protection**: Treats all high-frequency behaviors as preferences
3. **No semantic awareness**: Ignores whether behaviors cluster meaningfully
4. **Deliberately simple**: Not optimized, making comparison clearer

### Expected Behavior

- **Will promote**: Any behavior with >= 5 reinforcements to CORE
- **Won't check**: Semantic coherence, clustering stability, density structure
- **Problem**: user_665390 has behaviors with 42, 41 reinforcements that our system refuses to classify as CORE

---

## 2. Comparison Metrics

### Primary Metrics

#### A. **CORE Classification Count**
- **Frequency Baseline**: Expected to classify 2-4 behaviors as CORE for user_665390
- **Stability System**: 0 CORE (by design - stability too low)
- **Interpretation**: Shows conservative bias of stability system

#### B. **False-Positive Rate Proxy**
Since we lack ground truth, use **cluster instability** as proxy for false positives:

```
FP_proxy = (# CORE behaviors with stability < 0.15) / (# total CORE behaviors)
```

- **Frequency Baseline**: Cannot measure stability → assume all are false positives if stability < 0.15
- **Stability System**: 0% by definition (absolute threshold gates)

#### C. **Precision-Recall Tradeoff**

**Precision Proxy**: % of CORE behaviors that meet stability threshold
- **Frequency**: Low (promotes unstable high-frequency behaviors)
- **Stability**: 100% (only promotes stable clusters)

**Recall Proxy**: % of high-frequency behaviors (>10 reinforcements) classified as CORE
- **Frequency**: High (promotes most high-frequency behaviors)
- **Stability**: Low (rejects unstable high-frequency behaviors)

---

### Secondary Metrics

#### D. **Agreement Rate**
- What % of behaviors are classified the same way by both methods?
- Where do they disagree most? (High frequency + low stability cases)

#### E. **Stability Distribution of Baseline CORE**
- For behaviors frequency baseline promotes, what are their actual stabilities?
- Shows what stability system prevents

---

## 3. Test Users

### Current User
✅ **user_665390** (N=15, 2 clusters, stabilities: 0.09, 0.02)

### Additional Users Needed

#### Target: 3-5 more users with varying characteristics

**Ideal Mix:**

1. **Small stable dataset** (N=12-18, stability >0.15)
   - Tests if both methods agree on stable preferences
   
2. **Medium sparse dataset** (N=25-35, low stability)
   - Tests if frequency over-promotes in medium data
   
3. **Very small dataset** (N=8-12)
   - Tests small-N behavior for both methods
   
4. **Balanced dataset** (N=20-25, mixed stabilities)
   - Some stable, some unstable clusters
   
5. **Single-cluster dataset** (N=15-20, one clear preference)
   - Tests if stability system recognizes genuinely stable preference

### How to Obtain

**Option A**: Use existing test users in `behavior_dataset/` folder  
**Option B**: Generate synthetic users with controlled properties  
**Option C**: Ask for volunteers (if this is production system)

---

## 4. Evaluation Protocol

### For Each User:

1. **Run Frequency Baseline**
   - Count reinforcements
   - Classify: CORE (>=5), SECONDARY (2-4), NOISE (<2)
   - Record classifications

2. **Run Stability System** (current implementation)
   - HDBSCAN clustering
   - Extract stabilities
   - Classify: CORE (stability >=0.15), INSUFFICIENT_EVIDENCE, NOISE
   - Record classifications

3. **Cross-Analysis**
   - Which behaviors does frequency promote that stability rejects?
   - What are the stabilities of frequency's CORE behaviors?
   - Agreement rate
   - Disagreement patterns

4. **Qualitative Assessment**
   - For disagreements: which method seems more appropriate?
   - Are frequency's promotions semantically coherent?
   - Are stability's rejections overly conservative?

---

## 5. Expected Results

### Hypothesis

**Frequency baseline will over-promote in sparse data**:
- Behaviors with high reinforcement but low semantic clustering
- Example: user_665390 behaviors with 42, 41 reinforcements but stability 0.09

**Stability system will be conservative**:
- Reject high-frequency behaviors if clustering is weak
- Reduce false-positive exposure at cost of delayed detection

### Success Criteria

System is successful if:

1. **Frequency baseline promotes behaviors with stability <0.15**
   - Shows it lacks quality gate
   
2. **Stability system prevents these promotions**
   - Shows conservative filter is working
   
3. **Agreement on genuinely stable preferences** (if any exist in test set)
   - Shows stability system isn't just rejecting everything
   
4. **Qualitative analysis confirms frequency promotions are premature**
   - Manual inspection of disagreement cases

---

## 6. Threshold Sensitivity Analysis

### Test Thresholds

Run stability system with three thresholds:
- **0.10** (relaxed)
- **0.15** (current)
- **0.20** (strict)

### Analysis

For each threshold, measure:
1. Number of CORE clusters
2. Stability range of CORE clusters
3. How many frequency-baseline CORE behaviors are rejected

### Expected Findings

- **0.10**: May allow some weak clusters (closer to frequency baseline)
- **0.15**: Current conservative setting
- **0.20**: Very strict (may reject most/all)

If results are **stable across 0.10-0.20** (qualitatively similar outcomes):
→ Shows threshold isn't fragile

If results **change dramatically**:
→ Need to document sensitivity and justify choice

---

## 7. Implementation Plan

### Phase 1: Implement Baseline (1-2 hours)

1. Create `src/evaluation/frequency_baseline.py`
2. Implement simple frequency counter
3. Test on user_665390
4. Verify it promotes 2-4 behaviors to CORE

### Phase 2: Multi-User Testing (2-3 hours)

1. Identify 3-5 additional users from existing data
2. Run both methods on each user
3. Record results in structured format (CSV or JSON)

### Phase 3: Comparison Analysis (2-3 hours)

1. Create comparison script
2. Calculate metrics (agreement rate, stability distributions)
3. Generate comparison tables
4. Identify disagreement patterns

### Phase 4: Threshold Sensitivity (1-2 hours)

1. Re-run stability system with 0.10, 0.20 thresholds
2. Compare CORE classification counts
3. Document behavioral changes

### Phase 5: Documentation (2-3 hours)

1. Create `EVALUATION_RESULTS.md`
2. Include tables, metrics, example cases
3. Add to thesis documentation
4. Update main documentation with findings

**Total Estimated Time**: 8-13 hours

---

## 8. Deliverables

### A. Code Artifacts

1. `src/evaluation/frequency_baseline.py` - Baseline implementation
2. `src/evaluation/comparison_runner.py` - Runs both methods
3. `src/evaluation/metrics_calculator.py` - Computes comparison metrics
4. `tests/test_evaluation.py` - Validation tests

### B. Data Artifacts

1. `evaluation_results.json` - Raw results for all users
2. `comparison_metrics.csv` - Aggregated metrics
3. `disagreement_cases.json` - Detailed disagreement analysis

### C. Documentation

1. `docs/EVALUATION_RESULTS.md` - Complete results report
2. `docs/EVALUATION_PLAN.md` - This document (updated with results)
3. Updated `docs/DENSITY_FIRST_INFERENCE_SYSTEM.md` - Reference findings

---

## 9. Limitations of This Evaluation

### What This Evaluation Does

✅ Shows **behavioral differences** between methods  
✅ Demonstrates **false-positive filtering** in stability system  
✅ Validates **threshold sensitivity** (or lack thereof)  
✅ Provides **multi-user evidence** for consistency

### What This Evaluation Does NOT Do

❌ **No ground truth**: Cannot measure true accuracy (no labeled preferences)  
❌ **No user feedback**: Cannot validate if rejections were correct  
❌ **No long-term tracking**: Cannot show if INSUFFICIENT_EVIDENCE eventually becomes CORE  
❌ **Limited user diversity**: Small sample, possibly biased  
❌ **No production validation**: Not tested in real recommendation system

### Scope Statement

This evaluation is sufficient for **Bachelor's thesis demonstration** that:
- The system behaves conservatively by design
- Frequency-based methods lack stability filtering
- Results are consistent across small user sample

It is **not sufficient** for production deployment claims or publication in research venues.

---

## 10. Risk Mitigation

### Risk 1: No stable clusters exist in test data

**Mitigation**: 
- Generate one synthetic user with known stable clusters
- Or explicitly state: "All test users had N<20 with unstable clustering"

### Risk 2: Frequency baseline looks too stupid

**Mitigation**:
- This is intentional - it's the naive approach
- Real-world systems might use frequency (Amazon "frequently bought together")

### Risk 3: Agreement rate is 90%+

**Mitigation**:
- Focus on disagreement cases (high frequency + low stability)
- Qualitative analysis of why stability rejection is appropriate

### Risk 4: Results are threshold-sensitive (0.10 vs 0.20 very different)

**Mitigation**:
- Document sensitivity honestly
- Use this to motivate future calibration work
- Shows awareness of limitation

---

## Next Steps

1. **Approve this plan** - Review and adjust evaluation approach
2. **Implement baseline** - Start with frequency-only classifier
3. **Identify test users** - Find 3-5 users with varying characteristics
4. **Run evaluation** - Execute comparison protocol
5. **Document results** - Create results report for thesis

---

**Status**: Awaiting approval to proceed with implementation  
**Estimated Completion**: 1-2 weeks part-time
