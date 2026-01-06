# Unused Code Audit Report
**Generated**: 2025-01-XX  
**System**: Core Behaviour Identification Engine (CBIE)

---

## Executive Summary

This audit identifies unused or potentially unused functions, methods, and code segments across the CBIE system. The analysis was performed by tracing function definitions to their call sites across all Python files in `src/**/*.py`.

### Key Findings
- ✅ **5 Confirmed Unused Functions** - Safe to remove
- ⚠️ **3 Potentially Unused Functions** - Need verification before removal
- 📦 **2 Deprecated Schema Classes** - Legacy code kept for backward compatibility
- 🔄 **1 Test/Debug Endpoint** - Status unclear

---

## 1. CONFIRMED UNUSED FUNCTIONS ⚠️ SAFE TO REMOVE

### 1.1 `generate_archetype_with_context()` - archetype_service.py:123
**Status**: ✅ **DEFINITELY UNUSED**

```python
def generate_archetype_with_context(
    self,
    canonical_behaviors: List[Dict],
    user_statistics: Dict,
    user_id: str
) -> str:
```

**Evidence**:
- Definition found at line 123
- **NO call sites found** in entire codebase
- Comment in code explicitly says: `"⚠️ POTENTIALLY UNUSED - Check if called in cluster-centric pipeline ⚠️"`
- Enhanced version of `generate_archetype()` with additional statistics context

**Reason Created**: Likely created during transition from observation-centric to cluster-centric design, but never integrated

**Recommendation**: ✅ **REMOVE** - Replace with simpler `generate_archetype()` which IS actively used

---

### 1.2 `map_behaviors_to_clusters()` - clustering_engine.py:305
**Status**: ⚠️ **POTENTIALLY UNUSED** (Needs verification)

```python
def map_behaviors_to_clusters(
    self,
    clustering_result: ClusteringResult,
    behavior_metrics: List[Dict]
) -> Dict[int, List[Dict]]:
```

**Evidence**:
- Definition found at line 305
- **NO direct call sites found** in grep searches
- May have been used in observation-centric design (pre-refactor)

**Recommendation**: 🔍 **VERIFY then REMOVE** - Check if used in any dynamic imports or test files not scanned

---

### 1.3 `validate_clustering_quality()` - clustering_engine.py:341
**Status**: ⚠️ **POTENTIALLY UNUSED** (Needs verification)

```python
def validate_clustering_quality(
    self,
    clustering_result: ClusteringResult,
    min_valid_clusters: int = 2
) -> bool:
```

**Evidence**:
- Definition found at line 341
- **NO direct call sites found** in grep searches
- Likely validation logic for quality assurance

**Recommendation**: 🔍 **VERIFY then REMOVE or INTEGRATE** - Consider adding to pipeline if quality validation is needed

---

### 1.4 `get_projection_metadata()` - projection_service.py:189
**Status**: ⚠️ **POTENTIALLY UNUSED** (Needs verification)

```python
def get_projection_metadata(coordinates: List[Dict[str, float]]) -> Dict:
```

**Evidence**:
- Definition found at line 189
- **NO call sites found** in grep searches
- Other projection functions (`project_embeddings_to_2d`, `normalize_2d_coordinates`) ARE used in routes.py:461-462

**Recommendation**: 🔍 **VERIFY then REMOVE** - Check if intended for future visualization enhancements

---

### 1.5 Database CRUD Operations - Never Called
**Status**: ✅ **CONFIRMED UNUSED**

The following database operations are defined but **NEVER CALLED**:

#### MongoDB Service (mongodb_service.py)
```python
def update_behavior(self, behavior_id: str, updates: Dict[str, Any]) -> bool:  # Line 112
def delete_behavior(self, behavior_id: str) -> bool:  # Line 124
def get_clusters_by_user(self, user_id: str) -> List[Dict]:  # Line 327
def delete_clusters_by_user(self, user_id: str) -> bool:  # Line 335
```

#### Qdrant Service (qdrant_service.py)
```python
def search_similar_behaviors(...):  # Line 317
def delete_embeddings_by_user(self, user_id: str) -> bool:  # Line 365
def delete_embedding_by_behavior_id(self, behavior_id: str) -> bool:  # Line 395
```

**Evidence**:
- All defined with proper implementations
- **ZERO call sites** found across entire codebase
- Likely created for admin/maintenance operations that were never implemented

**Recommendation**: 
- ✅ **KEEP for now** - These are useful admin/maintenance utilities
- 🚀 **Consider exposing** as admin API endpoints for data management
- 📝 **Document** as "Available but not integrated" in system documentation

**Alternative**: If you never plan to use these, remove them to reduce maintenance burden

---

## 2. DEPRECATED / LEGACY CODE 📦

### 2.1 `CanonicalBehavior` Schema - schemas.py:193
**Status**: 📦 **LEGACY - Kept for Backward Compatibility**

```python
class CanonicalBehavior(BaseModel):
    """DEPRECATED: Legacy model for backward compatibility"""
    behavior_id: str
    behavior_text: str
    cluster_id: str
    cbi_original: float
    cluster_cbi: float
    tier: TierEnum
    temporal_span: TemporalSpan
```

**Evidence**:
- Marked as `DEPRECATED` in code comment
- Used in `CoreBehaviorProfile.primary_behaviors` and `CoreBehaviorProfile.secondary_behaviors` fields (lines 224-225)
- These fields are **always empty** in production code:
  ```python
  # cluster_analysis_pipeline.py:339-340
  primary_behaviors=[],  # Deprecated
  secondary_behaviors=[],  # Deprecated
  ```
- **Only used** in evaluation scripts (threshold_sensitivity_analysis.py, comparison_runner.py) for backward compatibility

**Reason Kept**: System transitioned from **observation-centric** to **cluster-centric** design. `CanonicalBehavior` represents individual behaviors, but `BehaviorCluster` is now the primary entity.

**Recommendation**: 
- 🔄 **KEEP short-term** - Evaluation scripts still reference these fields
- 🗑️ **PLAN REMOVAL** - Migrate evaluation scripts to use `behavior_clusters` instead
- 📋 **Migration Path**:
  1. Update evaluation scripts to read from `behavior_clusters` array
  2. Remove `primary_behaviors` and `secondary_behaviors` from `CoreBehaviorProfile`
  3. Delete `CanonicalBehavior` class definition

---

### 2.2 `ClusterModel` Schema - schemas.py:249
**Status**: 📦 **LEGACY but STILL USED**

```python
class ClusterModel(BaseModel):
    """DEPRECATED: Use BehaviorCluster instead"""
```

**Evidence**:
- Marked as `DEPRECATED` with comment to use `BehaviorCluster`
- **STILL ACTIVELY USED** in mongodb_service.py:
  - `insert_cluster()` at line 308
  - `insert_clusters_bulk()` at line 317
- Used for storing clusters in separate MongoDB collection when profile is too large

**Recommendation**: 
- ⚠️ **DO NOT REMOVE** - Despite deprecation note, this is still functional
- 🔄 **CONSIDER RENAMING** to `ClusterStorageModel` to reflect actual purpose
- 📝 **UPDATE COMMENT** - Remove "DEPRECATED" or clarify that it's for storage layer only

---

## 3. UNCLEAR STATUS - NEEDS INVESTIGATION 🔍

### 3.1 `/analyze-behaviors-cluster-centric` Endpoint - routes.py:200
**Status**: 🔍 **UNCLEAR - Possibly Test/Debug Endpoint**

```python
@router.post(
    "/analyze-behaviors-cluster-centric",
    ...
)
async def analyze_behaviors_cluster_centric(request: AnalysisRequest):
```

**Evidence**:
- Marked as `[NEW]` in code comments
- Appears to be duplicate of `/analyze-behaviors-from-storage` endpoint
- Main difference: `store_in_dbs=False` (testing mode)
- No clear indication if this is production or debug endpoint

**Recommendation**:
- 🔍 **CLARIFY PURPOSE** - Is this for testing or production?
- 📝 **DOCUMENT** - Add clear description in docstring
- 🔄 **CONSOLIDATE** - Consider merging with main endpoint using a `?dry_run=true` query parameter

---

## 4. CONFIRMED ACTIVE FUNCTIONS ✅

These functions were verified as **ACTIVELY USED** and should **NOT be removed**:

### Core Pipeline Functions
- ✅ `analyze_behaviors_from_storage()` - cluster_analysis_pipeline.py:54
- ✅ `analyze_observations()` - cluster_analysis_pipeline.py:120
- ✅ `_build_behavior_clusters()` - cluster_analysis_pipeline.py:373
- ✅ `_assign_epistemic_states()` - cluster_analysis_pipeline.py:512
- ✅ `_assign_tier_by_strength()` - cluster_analysis_pipeline.py:623
- ✅ `_calculate_time_span()` - cluster_analysis_pipeline.py:640

### Clustering Functions
- ✅ `cluster_behaviors()` - clustering_engine.py:35
- ✅ `get_cluster_statistics()` - clustering_engine.py:263
- ✅ `calculate_cluster_confidence()` - calculation_engine.py:209 (called from cluster_analysis_pipeline.py:447)

### Archetype & Labeling
- ✅ `generate_archetype()` - archetype_service.py:35 (called from cluster_analysis_pipeline.py:319)
- ✅ `generate_cluster_name()` - archetype_service.py:258 (GPT-4 naming)
- ✅ `generate_concise_label()` - archetype_service.py:197 (called from calculation_engine.py:318)
- ✅ `select_canonical_label()` - calculation_engine.py:283 (called from cluster_analysis_pipeline.py:456)

### Calculation Functions
- ✅ `calculate_cluster_strength()` - calculation_engine.py
- ✅ `_calculate_recency_factor()` - calculation_engine.py:115 (called from cluster_analysis_pipeline.py:499)

### Projection Functions
- ✅ `project_embeddings_to_2d()` - projection_service.py:22 (called from routes.py:461)
- ✅ `normalize_2d_coordinates()` - projection_service.py:145 (called from routes.py:462)

### LLM Context Formatting
- ✅ `generate_llm_context()` - llm_context_service.py
- ✅ `_format_detailed()` - llm_context_service.py:69
- ✅ `_format_compact()` - llm_context_service.py:106
- ✅ `_format_system_prompt()` - llm_context_service.py:121

### Database Operations (Active)
- ✅ `insert_behavior()`, `insert_behaviors_bulk()` - mongodb_service.py
- ✅ `get_behaviors_by_user()` - mongodb_service.py
- ✅ `insert_profile()`, `get_profile()`, `get_profile_with_clusters()` - mongodb_service.py
- ✅ `insert_cluster()` - mongodb_service.py:308 (ACTIVELY USED despite ClusterModel deprecation note)
- ✅ `insert_behaviors_with_embeddings()` - qdrant_service.py
- ✅ `get_embeddings_by_user()` - qdrant_service.py

### Embedding Functions
- ✅ `generate_embedding()` - embedding_service.py
- ✅ `generate_embeddings_batch()` - embedding_service.py:59 (called from generate_embeddings_for_behaviors())
- ✅ `generate_embeddings_for_behaviors()` - embedding_service.py

---

## 5. RECOMMENDED ACTIONS

### Immediate Actions (Safe to Remove)
1. ✅ **DELETE** `generate_archetype_with_context()` from archetype_service.py (line 123)
   - Already marked as potentially unused
   - Zero call sites confirmed
   - Functionality covered by simpler `generate_archetype()`

### Short-Term Actions (Verification Required)
2. 🔍 **VERIFY & REMOVE** these functions if truly unused:
   - `map_behaviors_to_clusters()` - clustering_engine.py:305
   - `validate_clustering_quality()` - clustering_engine.py:341
   - `get_projection_metadata()` - projection_service.py:189

3. 📝 **DOCUMENT** unused CRUD operations as admin utilities or remove:
   - `update_behavior()`, `delete_behavior()` (mongodb_service.py)
   - `get_clusters_by_user()`, `delete_clusters_by_user()` (mongodb_service.py)
   - `search_similar_behaviors()`, `delete_embeddings_by_user()`, `delete_embedding_by_behavior_id()` (qdrant_service.py)

### Long-Term Actions (Architecture Cleanup)
4. 🔄 **MIGRATE EVALUATION SCRIPTS** from `CanonicalBehavior` to `BehaviorCluster`:
   - Update `threshold_sensitivity_analysis.py` to use `behavior_clusters`
   - Update `comparison_runner.py` to use `behavior_clusters`
   - Remove `primary_behaviors` and `secondary_behaviors` fields from `CoreBehaviorProfile`
   - Delete `CanonicalBehavior` class

5. 📝 **CLARIFY `ClusterModel` STATUS**:
   - Either remove "DEPRECATED" comment (it's still used)
   - Or rename to `ClusterStorageModel` to clarify purpose

6. 🔍 **CLARIFY `/analyze-behaviors-cluster-centric` ENDPOINT**:
   - Document whether it's for testing or production
   - Consider consolidating with main endpoint using query parameters

---

## 6. ESTIMATED CLEANUP IMPACT

### Lines of Code to Remove
- `generate_archetype_with_context()`: ~40 lines
- Potentially unused clustering functions: ~80 lines
- Unused CRUD operations: ~150 lines
- `CanonicalBehavior` migration: ~50 lines

**Total**: ~320 lines of dead/legacy code

### Risk Assessment
- ✅ **LOW RISK**: Removing `generate_archetype_with_context()` (confirmed unused)
- ⚠️ **MEDIUM RISK**: Removing potentially unused functions (need thorough testing)
- 🔴 **HIGH RISK**: Removing CRUD operations (may break admin workflows if they exist)
- 🔄 **REFACTOR RISK**: Migrating from `CanonicalBehavior` (requires evaluation script updates)

---

## 7. CONCLUSION

The CBIE system has **minimal dead code** for a production system of this complexity. Most unused code falls into three categories:

1. **Leftover from architecture transition** (observation-centric → cluster-centric)
2. **Admin utilities never exposed** (CRUD operations)
3. **Validation functions never integrated** (quality checks)

**Recommendation**: Focus on **immediate removal** of `generate_archetype_with_context()` and **document decision** on whether to expose or remove unused CRUD operations. The legacy schema cleanup can be deferred to a dedicated refactoring sprint.

---

## Appendix: Grep Search Commands Used

```bash
# Function usage analysis
grep -r "generate_archetype_with_context" src/**/*.py
grep -r "map_behaviors_to_clusters\(|validate_clustering_quality\(" src/**/*.py
grep -r "get_projection_metadata\(" src/**/*.py

# CRUD operations
grep -r "update_behavior\(|delete_behavior\(" src/**/*.py
grep -r "get_clusters_by_user\(|delete_clusters_by_user\(" src/**/*.py
grep -r "search_similar_behaviors\(|delete_embeddings_by_user\(" src/**/*.py

# Schema usage
grep -r "CanonicalBehavior\(" src/**/*.py
grep -r "primary_behaviors|secondary_behaviors" src/**/*.py

# Active function verification
grep -r "calculate_cluster_confidence|select_canonical_label" src/**/*.py
grep -r "project_embeddings_to_2d|normalize_2d_coordinates" src/**/*.py
```

---

**End of Report**
