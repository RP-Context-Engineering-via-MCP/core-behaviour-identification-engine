# CBIE System Critical Evaluation — 2026-01-06

This document captures the current system’s inputs, end-to-end flow, clustering behavior, core behavior identification logic, calculations used, outputs, observed weaknesses, and a clear description of the correct (intended) flow.

## Scope
- Evaluate the cluster-centric pipeline implemented in the current codebase.
- Use production logs from recent runs on demo users.
- Identify logic gaps and recommend improvements while documenting the current behavior faithfully.

## Inputs
- Vector embeddings: 3072-dim text embeddings stored in Qdrant collection `behavior_embeddings`.
  - Source: [src/database/qdrant_service.py](src/database/qdrant_service.py)
- Behavior observations: Per-prompt behavior items with credibility, clarity, extraction confidence, timestamps, and prompt IDs.
  - Schema: [src/models/schemas.py](src/models/schemas.py)
- Prompts: User prompts with timestamps and optional token counts from MongoDB.
  - Source: [src/database/mongodb_service.py](src/database/mongodb_service.py)
- Configuration: Clustering and thresholds via `settings`.
  - Referenced across services (e.g., [src/services/clustering_engine.py](src/services/clustering_engine.py)).

## Current Flow (Cluster-Centric)
Implemented in [src/services/cluster_analysis_pipeline.py](src/services/cluster_analysis_pipeline.py):
1. Storage fetch: Load embeddings and observation metadata from Qdrant; load prompts from MongoDB.
2. Observation metrics: Compute per-observation simple quality metrics (`bw`, `abw`) via arithmetic mean.
3. Embeddings check: Ensure each observation has an embedding (already true for storage path).
4. Clustering: Run HDBSCAN on normalized embeddings; collect labels, stabilities (persistence), and intra-cluster distances.
5. Cluster construction: Aggregate observations into `BehaviorCluster` objects; label clusters via LLM for concise labels and names.
6. Epistemic classification: Assign `CORE`, `INSUFFICIENT_EVIDENCE`, or `NOISE` based on cluster stability and credibility median.
7. Persistence: Update behaviors in MongoDB with cluster IDs and epistemic states; store profile and cluster summaries.
8. Projection (for visualization): Run UMAP to 2D for all observations and return analysis summary.

## Clustering Behavior
- Engine: HDBSCAN with parameters defined in [src/services/clustering_engine.py](src/services/clustering_engine.py).
  - `min_cluster_size`: Adaptive. For small datasets (N<20), uses max(3, int(20% of N)); for N≥20, uses max(3, int(log(N))).
  - `min_samples`: 1 (sparse neighborhood requirement).
  - `cluster_selection_epsilon`: 0.15.
  - Metric: `euclidean` on L2-normalized vectors (to approximate cosine clustering).
- Weighted density claim vs reality:
  - Logs show attempt to use `sample_weight` with credibility, followed by “HDBSCAN sample_weight not supported, proceeding without weights.”
  - Current clustering is effectively unweighted; credibility does not influence the clustering process.
- Outputs captured per cluster:
  - Size, stability (persistence), mean/std/min/max intra-cluster distances, labels.

## Core Behavior Identification Logic
- Canonical labels and cluster names via LLM in [src/services/archetype_service.py](src/services/archetype_service.py), informed by cluster observations’ wording variations.
- Archetype generation (user-level) aggregates canonical behaviors; in demos, strong CORE clusters can drive archetype like “Visual Learner”.
- Epistemic classification rule (as used at runtime):
  - Compute median cluster stability and a fixed absolute CORE threshold (0.15).
  - A cluster is `CORE` if its stability ≥ 0.15 (absolute threshold). Tier assignment follows (`PRIMARY` for stronger ones).
  - If not CORE: classify as `INSUFFICIENT_EVIDENCE` when mean credibility ≥ global median credibility across observations.
  - Else: classify as `NOISE`.

## Calculations Used
- Per-observation metrics (in [src/services/calculation_engine.py](src/services/calculation_engine.py)):
  - `calculate_behavior_metrics()`: `quality_score = mean(credibility, clarity_score, extraction_confidence)`; returned as both `bw` and `abw`.
- Cluster-level metrics collected by the clustering engine:
  - Stability (HDBSCAN persistence).
  - Intra-cluster distances: mean, std, min, max.
- Additional calculation utilities exist (e.g., `calculate_cluster_confidence`, recency factors, cluster strength), but current epistemic assignment in logs relies primarily on the stability threshold and credibility median rule rather than these composites.

## Outputs
- BehaviorClusters with:
  - Observation members and metadata.
  - LLM-derived concise labels and cluster names.
  - Epistemic states: `CORE`, `INSUFFICIENT_EVIDENCE`, `NOISE`.
- User profile (MongoDB) containing lightweight cluster summaries and (optionally) an archetype.
- 2D projections for visualization via UMAP in [src/services/projection_service.py](src/services/projection_service.py).
- API responses in [src/api/routes.py](src/api/routes.py):
  - Analyze from storage, list core behaviors, LLM context, analysis summary, threshold simulation.

## Observed Behavior (Demo Users)
From recent logs:
- user_demo_epistemic (N=19):
  - Clusters formed: 4; stabilities ≈ 0.0035, 0.0217, 0.0469, 0.1444; noise observations: 3.
  - Epistemic result: 0 CORE, 2 INSUFFICIENT_EVIDENCE (cred ≥ median), 2 NOISE.
  - Summary returns 19 total behaviors (0 CORE, 7 INSUFFICIENT, 12 NOISE); no strong archetype.
- user_demo_single_core (N=20):
  - Clusters formed: 3; stabilities ≈ 0.3793, 0.1052, 0.0269; noise observations: 2.
  - Epistemic result: 1 CORE (stability 0.3793 ≥ 0.15), 1 INSUFFICIENT_EVIDENCE, 1 NOISE.
  - Summary returns 20 total behaviors (3 CORE, 11 INSUFFICIENT, 6 NOISE); archetype: “Visual Learner”.

## Weaknesses and Risks
1. Credibility-weighted clustering is not implemented:
   - HDBSCAN ignores `sample_weight`; current clustering is unweighted despite design intent.
2. Rigid absolute stability threshold (0.15):
   - For small N or diverse topics, produces 0 CORE even for relatively cohesive clusters.
3. Over-reliance on global credibility median:
   - `INSUFFICIENT_EVIDENCE` vs `NOISE` split can be brittle, ignoring intra-cluster cohesion and temporal factors.
4. Underuse of existing signals:
   - Intra-cluster distances, clarity distributions, and temporal span are computed but not integrated into epistemic classification.
5. Threshold simulation route inconsistency:
   - For `user_demo_single_core`, simulating threshold=0.15 reported 0 CORE while the pipeline earlier produced a CORE at stability 0.3793; suggests route logic mismatch.

## Correct (Intended) Flow Description
A reference flow that aligns code, logs, and design goals:
1. Fetch data
   - Load observations + embeddings from Qdrant; prompts from MongoDB.
2. Prepare metrics
   - Compute observation quality (`bw`, `abw`). Ensure embeddings present.
3. Cluster
   - L2-normalize embeddings; run HDBSCAN with N-adaptive `min_cluster_size` and tuned `min_samples`.
   - If weighting is desired, either pre-process distances to reflect credibility or apply weighting post-cluster in classification.
4. Build clusters
   - Aggregate members, compute stabilities and intra-cluster distance stats.
   - Generate concise labels and cluster names via LLM.
5. Classify epistemic states (robust rule)
   - Define dynamic stability threshold from data distribution (e.g., max(abs threshold, Q3 of stability)).
   - Integrate cluster confidence: combine stability, intra-cluster cohesion, clarity consistency, and temporal span.
   - Decide `CORE`/`INSUFFICIENT`/`NOISE` with transparent criteria.
6. Persist and summarize
   - Update MongoDB behaviors and store profile + cluster summaries.
   - Provide UMAP projections and analysis summary via API.
7. Simulation (consistency)
   - Ensure simulation endpoint applies identical classification logic with a parameterized threshold and returns diffs.

## Recommendations (Targeted)
- Implement credibility influence:
  - If HDBSCAN must remain: simulate weights via controlled duplication or adjust distance pre-processing.
  - Alternatively, consider algorithms with native weighting or leverage HDBSCAN soft probabilities downstream.
- Dynamic thresholds:
  - Replace fixed 0.15 with data-aware thresholds (quartiles or mean+sigma), especially for N<50.
- Integrate `calculate_cluster_confidence()`:
  - Use cohesion and clarity to refine `CORE`/`INSUFFICIENT` decisions.
- Tune `min_samples`:
  - Use `max(2, int(log(N)))` to reduce fragile clusters.
- Fix simulation route:
  - Align its logic and scales with the pipeline; include per-cluster details and a summary diff.
- Logging & docs:
  - Remove “weighted density” claim until implemented; log which signals drive epistemic decisions.

## File References
- Pipeline: [src/services/cluster_analysis_pipeline.py](src/services/cluster_analysis_pipeline.py)
- Clustering engine: [src/services/clustering_engine.py](src/services/clustering_engine.py)
- Calculation engine: [src/services/calculation_engine.py](src/services/calculation_engine.py)
- Archetype service: [src/services/archetype_service.py](src/services/archetype_service.py)
- Projection service: [src/services/projection_service.py](src/services/projection_service.py)
- API routes: [src/api/routes.py](src/api/routes.py)
- MongoDB service: [src/database/mongodb_service.py](src/database/mongodb_service.py)
- Qdrant service: [src/database/qdrant_service.py](src/database/qdrant_service.py)
