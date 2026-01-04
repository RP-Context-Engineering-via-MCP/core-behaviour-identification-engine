# Frontend Demo Integration Analysis

**Date**: January 4, 2026  
**Branch**: `frontend-demo-integration`  
**Status**: ⚠️ **Partial Compatibility - API Extensions Required**

---

## Executive Summary

The frontend demo is a React-based AI Studio application that **can be partially integrated** with our existing CBIE APIs. However, it currently uses **mock data generators** and connects to **Google Gemini AI** for chat functionality, rather than our backend APIs.

### Key Findings

✅ **What Works Out of the Box**:
- Data structure alignment (clusters, behaviors, confidence scoring)
- Epistemic state concepts (CORE/INSUFFICIENT/NOISE)
- Stability-based filtering logic
- User profile switching pattern

❌ **What Needs Changes**:
- Frontend currently uses mock data instead of API calls
- Chat interface connects to Gemini directly (not our LLM context service)
- User authentication/session management not implemented
- No backend persistence integration
- Missing several API endpoints the demo would need

---

## Current Frontend Architecture

### Tech Stack
```json
{
  "framework": "React 19.2.3",
  "language": "TypeScript",
  "build_tool": "Vite 6.2.0",
  "ai_integration": "@google/genai ^1.34.0"
}
```

### Core Features
1. **Analysis Dashboard** - Displays user profile metrics
2. **Raw vs Inference** - Shows behavior classification
3. **Embedding Space** - 2D visualization of behavior clusters
4. **Cluster Inspector** - Stability threshold testing
5. **Baseline Comparison** - Density vs frequency comparison
6. **Threshold Lab** - Interactive parameter tuning
7. **Context-Aware Chat** - LLM personalization demo

### User Profiles (Mock Data)
```typescript
const USERS: UserProfile[] = [
  { id: 'u1', name: 'Sparse User (Alex)', type: 'sparse', ... },
  { id: 'u2', name: 'Dense/Noisy User (Sam)', type: 'dense', ... },
  { id: 'u3', name: 'Clean User (Jordan)', type: 'clean', ... },
];
```

**Issue**: These are hardcoded test cases, not real user IDs from your database.

---

## Data Structure Comparison

### ✅ Compatible Structures

#### 1. Behavior Cluster Model

**Frontend Expects**:
```typescript
interface Behavior {
  id: string;
  text: string;
  credibility: number;
  timestamp: number;
  source: string;
  embedding: { x: number; y: number }; // 2D projection
  clusterId: string | null;
  clusterName?: string;
  clusterStability: number;
}

interface ClusterData {
  id: string;
  name: string;
  stability: number;
  size: number;
  isCore: boolean;
}
```

**Backend Provides** (`BehaviorCluster` schema):
```python
class BehaviorCluster(BaseModel):
    cluster_id: str
    cluster_name: Optional[str]
    cluster_stability: Optional[float]
    cluster_size: int
    observations: List[BehaviorObservation]
    epistemic_state: EpistemicState  # CORE, INSUFFICIENT_EVIDENCE, NOISE
    cluster_strength: float
    confidence: float
```

**Mapping**:
- ✅ `cluster_id` → `id`
- ✅ `cluster_name` → `name`
- ✅ `cluster_stability` → `stability`
- ✅ `cluster_size` → `size`
- ✅ `epistemic_state == CORE` → `isCore = true`

#### 2. Analysis Metrics

**Frontend Expects**:
```typescript
interface AnalysisResult {
  metrics: {
    totalObservations: number;
    coreClusters: number;
    insufficientEvidence: number;
    noiseObservations: number;
  };
}
```

**Backend Can Provide**:
- `totalObservations` → Sum of all `cluster_size` values
- `coreClusters` → Count where `epistemic_state == CORE`
- `insufficientEvidence` → Count where `epistemic_state == INSUFFICIENT_EVIDENCE`
- `noiseObservations` → Count where `epistemic_state == NOISE`

---

## API Gap Analysis

### Existing APIs (Available Now)

| Endpoint | Method | Status | Frontend Usable? |
|----------|--------|--------|------------------|
| `/api/v1/analyze-behaviors-from-storage` | POST | ✅ Active | ⚠️ Partial |
| `/api/v1/get-user-profile/{user_id}` | GET | ✅ Active | ✅ Yes |
| `/api/v1/list-core-behaviors/{user_id}` | GET | ✅ Active | ✅ Yes |
| `/api/v1/analyze-behaviors-cluster-centric` | POST | ✅ Active | ⚠️ Partial |
| `/api/v1/profile/{user_id}/llm-context` | GET | ✅ Active | ✅ Yes |
| `/api/v1/health` | GET | ✅ Active | ✅ Yes |
| `/api/v1/test-users` | GET | ✅ Active | ✅ Yes |

### Missing APIs (Need to Create)

#### 1. **GET** `/api/v1/profile/me/analysis-summary`

**Purpose**: Provide dashboard metrics for current user

**Frontend Needs**:
```typescript
{
  behaviors: Behavior[],
  clusters: ClusterData[],
  metrics: {
    totalObservations: number,
    coreClusters: number,
    insufficientEvidence: number,
    noiseObservations: number
  }
}
```

**Current Gap**: 
- No single endpoint returns this combined format
- Frontend would need to call 2-3 endpoints and merge data
- No 2D embedding projection available (frontend generates mock coordinates)

**Recommended Implementation**:
```python
@router.get("/profile/{user_id}/analysis-summary")
async def get_analysis_summary(user_id: str):
    """
    Returns analysis dashboard data with 2D projections
    """
    profile = mongodb_service.get_profile(user_id)
    
    # Generate 2D embeddings using UMAP
    behaviors_with_2d = []
    for cluster in profile.behavior_clusters:
        for obs in cluster.observations:
            behaviors_with_2d.append({
                "id": obs.observation_id,
                "text": obs.behavior_text,
                "credibility": obs.credibility,
                "timestamp": obs.timestamp,
                "source": "system",
                "embedding": {"x": ..., "y": ...},  # UMAP projection
                "clusterId": cluster.cluster_id,
                "clusterName": cluster.cluster_name,
                "clusterStability": cluster.cluster_stability
            })
    
    # Calculate metrics
    core_clusters = [c for c in profile.behavior_clusters if c.epistemic_state == "CORE"]
    insufficient = [c for c in profile.behavior_clusters if c.epistemic_state == "INSUFFICIENT_EVIDENCE"]
    noise = [c for c in profile.behavior_clusters if c.epistemic_state == "NOISE"]
    
    return {
        "behaviors": behaviors_with_2d,
        "clusters": [...],
        "metrics": {...}
    }
```

#### 2. **POST** `/api/v1/profile/{user_id}/simulate-threshold`

**Purpose**: Interactive threshold tuning (Threshold Lab feature)

**Frontend Needs**:
```typescript
// Request
{ stabilityThreshold: number }

// Response
{ 
  coreClusters: number,
  updated_clusters: ClusterData[]
}
```

**Current Gap**: No endpoint for real-time threshold adjustment

**Recommended Implementation**:
```python
@router.post("/profile/{user_id}/simulate-threshold")
async def simulate_threshold(
    user_id: str, 
    stability_threshold: float = 0.15
):
    """
    Re-classify clusters based on new stability threshold
    Does NOT save changes - returns preview only
    """
    profile = mongodb_service.get_profile(user_id)
    
    # Re-classify each cluster
    updated_clusters = []
    for cluster in profile.behavior_clusters:
        is_core = cluster.cluster_stability >= stability_threshold
        updated_clusters.append({
            "id": cluster.cluster_id,
            "name": cluster.cluster_name,
            "stability": cluster.cluster_stability,
            "size": cluster.cluster_size,
            "isCore": is_core
        })
    
    core_count = sum(1 for c in updated_clusters if c["isCore"])
    
    return {
        "coreClusters": core_count,
        "updated_clusters": updated_clusters
    }
```

#### 3. **POST** `/api/v1/chat/context-aware`

**Purpose**: Replace direct Gemini integration with backend-managed LLM calls

**Frontend Currently Does**:
```typescript
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
const model = ai.models.generateContent({
   model: 'gemini-3-flash-preview',
   config: { systemInstruction },
   contents: [{ role: 'user', parts: [{ text: input }] }]
});
```

**Frontend Should Call Instead**:
```typescript
POST /api/v1/chat/context-aware
{
  "user_id": "user_123",
  "message": "Can you help me with Python?",
  "include_core_behaviors": true
}

Response:
{
  "response": "Since you're interested in Python development...",
  "behaviors_used": ["Python Dev", "Documentation Preference"],
  "confidence": 0.85
}
```

**Backend Would**:
- Fetch user's CORE behaviors from `/list-core-behaviors/{user_id}`
- Inject into system prompt
- Call Gemini with proper context
- Return response + metadata

**Benefits**:
- Centralized API key management
- Rate limiting and monitoring
- Consistent prompt engineering
- Cost tracking per user

#### 4. **GET** `/api/v1/users/list` (User Management)

**Purpose**: Replace hardcoded user list with real users

**Frontend Currently Has**:
```typescript
const USERS: UserProfile[] = [
  { id: 'u1', name: 'Sparse User (Alex)', type: 'sparse', ... },
  // ...
];
```

**Should Call Instead**:
```typescript
GET /api/v1/users/list

Response:
[
  {
    "user_id": "user_665390",
    "display_name": "User 665390",
    "profile_exists": true,
    "cluster_count": 5,
    "last_analyzed": 1735948800
  }
]
```

**Note**: You already have `/api/v1/test-users` which provides similar data! Just needs restructuring.

---

## Required Frontend Changes

### 1. Replace Mock Data with API Calls

**File**: `index.tsx` (Lines 115-145)

**Current**:
```typescript
const generateBehaviors = (userType: 'sparse' | 'dense' | 'clean'): Behavior[] => {
  const behaviors: Behavior[] = [];
  // ... mock data generation
  return behaviors;
};
```

**Should Be**:
```typescript
const fetchAnalysisData = async (userId: string): Promise<AnalysisResult> => {
  const response = await fetch(`/api/v1/profile/${userId}/analysis-summary`);
  return await response.json();
};
```

### 2. Integrate Backend LLM Context Service

**File**: `index.tsx` (Lines 459-510)

**Current**:
```typescript
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
```

**Should Be**:
```typescript
const response = await fetch('/api/v1/chat/context-aware', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: user.id,
    message: input,
    include_core_behaviors: true
  })
});
```

### 3. Add Backend URL Configuration

**File**: `vite.config.ts`

**Add**:
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // Your FastAPI backend
        changeOrigin: true
      }
    }
  }
});
```

### 4. Replace Hardcoded Users

**File**: `index.tsx` (Lines 48-52)

**Current**:
```typescript
const USERS: UserProfile[] = [
  { id: 'u1', name: 'Sparse User (Alex)', type: 'sparse', ... },
];
```

**Should Be**:
```typescript
const [users, setUsers] = useState<UserProfile[]>([]);

useEffect(() => {
  fetch('/api/v1/test-users')
    .then(res => res.json())
    .then(data => setUsers(data.users));
}, []);
```

### 5. Implement 2D Embedding Projection

**Backend Needs**: Add UMAP dimensionality reduction

**Required Package**: `umap-learn`

**Implementation**:
```python
from umap import UMAP

def project_embeddings_2d(embeddings: List[List[float]]) -> List[Dict[str, float]]:
    """
    Project high-dimensional embeddings to 2D for visualization
    """
    if len(embeddings) < 3:
        # Fallback for small datasets
        return [{"x": 0, "y": 0} for _ in embeddings]
    
    reducer = UMAP(n_components=2, random_state=42)
    projections = reducer.fit_transform(embeddings)
    
    return [{"x": float(p[0]), "y": float(p[1])} for p in projections]
```

---

## New API Endpoints Summary

### Priority 1 (Critical for Integration)

#### 1. `GET /api/v1/profile/{user_id}/analysis-summary`
- Returns dashboard metrics + 2D projections
- Replaces mock data generator
- **Effort**: Medium (2-3 hours)

#### 2. `POST /api/v1/chat/context-aware`
- Backend-managed LLM calls with CBIE context
- Replaces direct Gemini integration
- **Effort**: High (4-5 hours)

### Priority 2 (Enhanced Features)

#### 3. `POST /api/v1/profile/{user_id}/simulate-threshold`
- Interactive threshold tuning
- Powers "Threshold Lab" feature
- **Effort**: Low (1-2 hours)

#### 4. `GET /api/v1/users/list` (or refactor `/test-users`)
- Dynamic user list
- **Effort**: Low (1 hour)

---

## Authentication & Session Management

### Current State
- ❌ No authentication in frontend
- ❌ No session management
- ❌ No user-scoped API access

### Recommended Approach

**Option 1: Session-Based (Simplest for Demo)**
```typescript
// Frontend login
const response = await fetch('/api/v1/auth/login', {
  method: 'POST',
  body: JSON.stringify({ user_id: 'user_665390' }),
  credentials: 'include'  // Send cookies
});

// Backend sets session cookie
// All subsequent API calls automatically scoped to user
```

**Option 2: JWT Token-Based (Production-Ready)**
```typescript
// Frontend stores token
const token = localStorage.getItem('auth_token');
const response = await fetch('/api/v1/profile/me', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**Backend Implementation**:
```python
from fastapi import Depends, HTTPException

async def get_current_user_id(
    authorization: str = Header(None)
) -> str:
    if not authorization:
        raise HTTPException(status_code=401)
    
    # Validate token and extract user_id
    user_id = validate_jwt(authorization)
    return user_id

@router.get("/profile/me")
async def get_my_profile(
    user_id: str = Depends(get_current_user_id)
):
    # user_id is automatically extracted from token
    return get_profile(user_id)
```

---

## Environment Configuration

### Frontend `.env.local`

**Current**:
```env
GEMINI_API_KEY=PLACEHOLDER_API_KEY
```

**Should Be**:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_ENABLE_MOCK_MODE=false
```

### Backend Configuration

**Add to `src/config.py`**:
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # LLM Integration
    GEMINI_API_KEY: str
    LLM_MODEL: str = "gemini-2.0-flash-exp"
    LLM_MAX_TOKENS: int = 1000
    
    # CORS for frontend
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]  # Vite default port
```

---

## Integration Roadmap

### Phase 1: Minimal Viable Integration (1-2 days)
1. ✅ Create `frontend-demo-integration` branch
2. ⏳ Implement Priority 1 APIs:
   - `/profile/{user_id}/analysis-summary`
   - `/chat/context-aware`
3. ⏳ Update frontend to call real APIs instead of mocks
4. ⏳ Add CORS configuration to FastAPI
5. ⏳ Test with existing user `user_665390`

### Phase 2: Enhanced Features (2-3 days)
1. ⏳ Implement Priority 2 APIs
2. ⏳ Add 2D embedding projection (UMAP)
3. ⏳ Implement user switching functionality
4. ⏳ Add error handling and loading states

### Phase 3: Production Readiness (3-5 days)
1. ⏳ Add authentication/authorization
2. ⏳ Implement rate limiting
3. ⏳ Add API monitoring
4. ⏳ Performance optimization
5. ⏳ Security hardening

---

## Testing Strategy

### Backend API Tests

**Add to `tests/test_api.py`**:
```python
def test_analysis_summary(client):
    response = client.get("/api/v1/profile/user_665390/analysis-summary")
    assert response.status_code == 200
    data = response.json()
    assert "behaviors" in data
    assert "clusters" in data
    assert "metrics" in data
    assert len(data["behaviors"]) > 0

def test_chat_context_aware(client):
    response = client.post("/api/v1/chat/context-aware", json={
        "user_id": "user_665390",
        "message": "Help me with Python",
        "include_core_behaviors": True
    })
    assert response.status_code == 200
    assert "response" in response.json()
```

### Frontend Integration Tests

**Create `frontend-demo/tests/integration.test.ts`**:
```typescript
describe('CBIE API Integration', () => {
  it('fetches analysis summary', async () => {
    const result = await fetchAnalysisData('user_665390');
    expect(result.metrics.totalObservations).toBeGreaterThan(0);
  });
  
  it('sends context-aware chat message', async () => {
    const response = await sendChatMessage('user_665390', 'Hello');
    expect(response.response).toBeDefined();
  });
});
```

---

## Security Considerations

### API Key Management
- ❌ **DON'T**: Expose `GEMINI_API_KEY` in frontend `.env.local`
- ✅ **DO**: Keep API key in backend only
- ✅ **DO**: Use backend as proxy for all LLM calls

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/chat/context-aware")
@limiter.limit("10/minute")
async def chat_endpoint(...):
    pass
```

---

## Cost Estimation

### Development Effort

| Task | Effort | Priority |
|------|--------|----------|
| New API endpoints | 8-10 hours | High |
| Frontend refactoring | 6-8 hours | High |
| Authentication | 4-6 hours | Medium |
| UMAP integration | 2-3 hours | Medium |
| Testing | 4-5 hours | High |
| **Total** | **24-32 hours** | **~3-4 days** |

### Infrastructure Requirements

**New Python Packages**:
```bash
pip install umap-learn slowapi python-jose[cryptography]
```

**No Additional Services Required**:
- ✅ MongoDB already configured
- ✅ Qdrant already configured
- ✅ FastAPI already set up

---

## Recommendations

### ✅ Proceed with Integration

**Reasons**:
1. Data structures are highly compatible
2. Minimal backend changes required (4 new endpoints)
3. Frontend is well-architected and easy to adapt
4. Demonstrates real system capabilities vs mock data
5. All core infrastructure already exists

### 🎯 Suggested Next Steps

1. **Immediate** (Today):
   - Implement `/profile/{user_id}/analysis-summary` endpoint
   - Test with existing user data (`user_665390`)

2. **Short-term** (This Week):
   - Implement `/chat/context-aware` endpoint
   - Update frontend to call real APIs
   - Add CORS configuration

3. **Medium-term** (Next Week):
   - Add authentication layer
   - Implement remaining Priority 2 APIs
   - Deploy to test environment

### ⚠️ Potential Blockers

1. **2D Embedding Projection**:
   - Requires UMAP library (not currently installed)
   - May be slow for large datasets (>1000 points)
   - **Mitigation**: Cache projections, use lazy loading

2. **LLM API Costs**:
   - Direct Gemini calls from frontend = uncontrolled costs
   - **Mitigation**: Backend proxy with rate limiting + caching

3. **User Data Availability**:
   - Frontend assumes multiple test users
   - Currently only `user_665390` has data
   - **Mitigation**: Generate synthetic test users or use existing

---

## Conclusion

**The frontend demo CAN be integrated with your existing CBIE system** with moderate effort. The data structures align well, and most required APIs are either present or straightforward to implement.

**Key Success Factors**:
- ✅ Strong architectural alignment
- ✅ Clear separation of concerns
- ✅ Existing infrastructure supports all features
- ✅ Well-documented APIs

**Primary Work Required**:
- 🔨 4 new API endpoints (~10 hours)
- 🔨 Frontend refactoring to use real APIs (~8 hours)
- 🔨 Authentication/security (~6 hours)
- 🔨 Testing and polish (~5 hours)

**Total Estimated Timeline**: 3-4 days of focused development

Would you like me to start implementing any of these changes?
