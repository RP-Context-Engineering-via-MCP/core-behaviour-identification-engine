# Frontend Demo Integration - Setup & Testing Guide

## Overview

The frontend demo has been fully integrated with the CBIE backend. This guide explains how to set up and test the integration.

## Architecture

```
Frontend (React + Vite)  →  Backend APIs (FastAPI)  →  MongoDB + Qdrant
         Port 3000              Port 8000
```

### Key Features Implemented

1. ✅ **2D Visualization** - UMAP projection of behavior embeddings
2. ✅ **Real-time Analysis** - Fetch user profiles from backend
3. ✅ **Threshold Simulation** - Interactive cluster re-classification
4. ✅ **LLM Context Injection** - Fetch CORE behaviors for personalization
5. ✅ **Dynamic User Loading** - List users from database

## Prerequisites

### Backend Requirements
- Python 3.8+
- MongoDB running (default: `localhost:27017`)
- Qdrant running (default: `localhost:6333`)
- User data loaded (e.g., `user_665390`)

### Frontend Requirements
- Node.js 16+
- npm or yarn

## Installation

### 1. Install Backend Dependencies

```powershell
cd d:\Academics\core-behaviour-identification-engine

# Install new dependency (UMAP for 2D projections)
pip install umap-learn

# Or install all requirements
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```powershell
cd frontend-demo
npm install
```

### 3. Configure Environment Variables

**Backend** (`src/config.py`):
- MongoDB connection settings
- Qdrant connection settings
- OpenAI API key (for embeddings)

**Frontend** (`frontend-demo/.env.local`):
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Running the Integration

### Terminal 1: Start Backend

```powershell
cd d:\Academics\core-behaviour-identification-engine

# Option 1: Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Using Python
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: `http://localhost:8000`

### Terminal 2: Start Frontend

```powershell
cd d:\Academics\core-behaviour-identification-engine\frontend-demo

npm run dev
```

Frontend will be available at: `http://localhost:3000`

## Testing the Integration

### 1. Health Check

Open browser and navigate to:
- Backend health: `http://localhost:8000/api/v1/health`
- Frontend: `http://localhost:3000`

Expected backend response:
```json
{
  "status": "healthy",
  "service": "CBIE MVP"
}
```

### 2. Test User Loading

**Frontend Action**: Page should load and display available users in the sidebar

**What happens**:
- Frontend calls `GET /api/v1/test-users`
- Backend returns list of users with behavior counts
- Dropdown populates with user options

**Check**:
- Sidebar shows "ACTIVE USER" dropdown
- At least one user is available (e.g., "User 665390")

### 3. Test Analysis Dashboard

**Frontend Action**: Click "Run Analysis" button on Dashboard page

**What happens**:
1. Frontend calls `GET /api/v1/profile/{user_id}/analysis-summary`
2. Backend:
   - Fetches user profile from MongoDB
   - Extracts all behavior observations
   - Projects embeddings to 2D using UMAP
   - Classifies clusters by epistemic state
   - Returns dashboard metrics

**Expected result**:
- Dashboard shows 4 metric cards:
  - Total Observations
  - CORE Clusters (green)
  - Insufficient Evidence (amber)
  - Noise Observations (gray)
- Values should match actual user data

**Check**:
```
Total Observations: > 0
CORE Clusters: >= 0 (may be 0 for sparse users)
```

### 4. Test 2D Embedding Visualization

**Frontend Action**: Navigate to "Embedding Space" page (page 3)

**What happens**:
- Uses data from analysis-summary endpoint
- Renders 2D scatter plot with color coding:
  - Green dots: CORE observations
  - Amber dots: INSUFFICIENT_EVIDENCE
  - Gray dots: NOISE

**Expected result**:
- Chart displays points in 2D space
- Points are clustered (not random scatter)
- Hover shows behavior text

**Check**:
- Visual clustering is apparent
- CORE behaviors form tight groups
- Noise points are scattered

### 5. Test Threshold Lab

**Frontend Action**: 
1. Navigate to "Threshold Lab" page (page 6)
2. Move the threshold slider

**What happens**:
1. Frontend calls `POST /api/v1/profile/{user_id}/simulate-threshold?stability_threshold={value}`
2. Backend re-classifies clusters without saving
3. Updates metric cards in real-time

**Expected result**:
- "Resulting Core Clusters" number updates immediately
- Higher threshold → fewer CORE clusters
- Lower threshold → more CORE clusters

**Check**:
```
Threshold = 0.05: Maximum CORE clusters
Threshold = 0.50: Minimum CORE clusters
```

### 6. Test LLM Context Injection

**Frontend Action**:
1. Navigate to "Context-Aware Chat" page (page 7)
2. Type a message and send

**What happens** (First Message):
1. Frontend calls `GET /api/v1/profile/{user_id}/llm-context`
2. Backend returns formatted context string with CORE behaviors only
3. Frontend injects context into LLM system prompt
4. Gemini generates personalized response

**Expected result**:
- Left panel shows "What the System Knows"
- CORE section displays verified behaviors
- INSUFFICIENT and NOISE sections show withheld data
- Chat response is personalized based on CORE behaviors

**Check**:
- If CORE clusters exist: Response mentions user's interests
- If no CORE clusters: Generic response (abstention mode)

### 7. Test Cluster Inspector

**Frontend Action**: Navigate to "Cluster Inspector" page (page 4)

**Expected result**:
- Table shows all clusters
- Columns: Cluster Name, Size, Stability Score, Threshold, Result, Visual
- "ACCEPTED" badge for CORE clusters (green)
- "REJECTED" badge for non-CORE clusters (red)
- Visual bar shows stability with threshold line

## API Endpoints Reference

### New Endpoints Implemented

#### 1. GET `/api/v1/profile/{user_id}/analysis-summary`

**Purpose**: Dashboard data with 2D projections

**Response**:
```json
{
  "user_id": "user_665390",
  "behaviors": [
    {
      "id": "obs_123",
      "text": "prefers visual learning",
      "credibility": 0.85,
      "timestamp": 1234567890,
      "source": "system",
      "embedding": {"x": -2.5, "y": 3.1},
      "clusterId": "cluster_0",
      "clusterName": "Visual Learning",
      "clusterStability": 0.25,
      "epistemicState": "CORE"
    }
  ],
  "clusters": [
    {
      "id": "cluster_0",
      "name": "Visual Learning",
      "stability": 0.25,
      "size": 12,
      "isCore": true,
      "epistemicState": "CORE",
      "confidence": 0.78,
      "clusterStrength": 2.5
    }
  ],
  "metrics": {
    "totalObservations": 50,
    "coreClusters": 3,
    "insufficientEvidence": 15,
    "noiseObservations": 10,
    "totalClusters": 8
  }
}
```

#### 2. POST `/api/v1/profile/{user_id}/simulate-threshold`

**Query Parameters**:
- `stability_threshold`: float (0.0 to 1.0)

**Response**:
```json
{
  "user_id": "user_665390",
  "stability_threshold": 0.20,
  "coreClusters": 2,
  "insufficientClusters": 4,
  "noiseClusters": 2,
  "metrics": {
    "coreClusters": 2,
    "insufficientEvidence": 25,
    "noiseObservations": 10
  },
  "updated_clusters": [...]
}
```

#### 3. GET `/api/v1/profile/{user_id}/llm-context` (Enhanced)

**Query Parameters**:
- `min_strength`: float (default: 30.0)
- `min_confidence`: float (default: 0.40)
- `max_behaviors`: int (default: 5)
- `include_archetype`: bool (default: true)

**Response**:
```json
{
  "user_id": "user_665390",
  "archetype": "Visual Learner",
  "context_string": "User Preferences:\n- Visual Learning (Strength: 85%, Confidence: 78%)\n...",
  "primary_behaviors": [
    {
      "label": "Visual Learning",
      "strength": 85.0,
      "confidence": 0.78
    }
  ],
  "metadata": {
    "behavior_count": 3,
    "min_strength": 30.0,
    "min_confidence": 0.40
  }
}
```

## Troubleshooting

### Frontend shows "Loading users from backend..." indefinitely

**Cause**: Backend not running or not accessible

**Solution**:
1. Check backend is running: `http://localhost:8000/api/v1/health`
2. Check console for errors (F12 → Console)
3. Verify proxy configuration in `vite.config.ts`

### "Failed to fetch analysis data" error

**Cause**: User has no profile in MongoDB

**Solution**:
1. Run analysis for the user first:
   ```powershell
   # Using curl or Postman
   POST http://localhost:8000/api/v1/analyze-behaviors-from-storage?user_id=user_665390
   ```

2. Or load test data:
   ```powershell
   cd test-data
   python load_realistic_evaluation_data.py
   ```

### 2D visualization shows points in a circle

**Cause**: UMAP not installed or failed, using fallback layout

**Solution**:
```powershell
pip install umap-learn
```

### Chat responses are generic (not personalized)

**Cause**: 
- No CORE behaviors for user (system abstains)
- Gemini API key not configured

**Solution**:
1. Check CORE clusters count in dashboard
2. If 0 CORE clusters: Expected behavior (abstention mode)
3. If >0 CORE clusters: Check `.env.local` has valid `GEMINI_API_KEY`

### CORS errors in browser console

**Cause**: Backend CORS not configured or frontend port changed

**Solution**: Check `main.py` has CORS middleware configured for frontend port:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Performance Notes

### 2D Projection Speed
- Small datasets (<100 points): < 1 second
- Medium datasets (100-1000 points): 1-3 seconds
- Large datasets (>1000 points): 3-10 seconds

**Optimization**: Consider caching UMAP projections in MongoDB

### Threshold Simulation Speed
- Instant (< 100ms) - only re-classifies existing clusters
- No re-embedding or re-clustering required

## Next Steps

### Recommended Enhancements

1. **Caching**: Cache UMAP projections to avoid recomputation
2. **Pagination**: For users with >1000 behaviors
3. **Filtering**: Add filters for date ranges, sources
4. **Export**: Download analysis results as JSON/CSV
5. **Comparison**: Side-by-side view of multiple users

### Production Checklist

- [ ] Add authentication/authorization
- [ ] Rate limiting on API endpoints
- [ ] Error monitoring (Sentry, etc.)
- [ ] Analytics tracking
- [ ] Performance monitoring
- [ ] Database connection pooling
- [ ] API response caching
- [ ] HTTPS/TLS configuration

## Summary

The integration is **fully functional** and demonstrates:

✅ Real-time data fetching from backend  
✅ 2D visualization of behavior embeddings (UMAP)  
✅ Interactive threshold tuning  
✅ LLM context injection from verified CORE behaviors  
✅ Dynamic user switching  
✅ Epistemic state filtering (CORE/INSUFFICIENT/NOISE)  

All critical features are working end-to-end without authentication, as requested.
