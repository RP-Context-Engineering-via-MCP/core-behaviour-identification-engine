# Frontend Demo Integration - Quick Start

This branch contains the fully integrated frontend demo with the CBIE backend.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ with dependencies installed
- Node.js 16+ 
- MongoDB running (localhost:27017)
- Qdrant running (localhost:6333)
- User data loaded (e.g., `user_665390`)

### Start Backend (Terminal 1)
```powershell
cd d:\Academics\core-behaviour-identification-engine
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend (Terminal 2)
```powershell
cd d:\Academics\core-behaviour-identification-engine\frontend-demo
npm install    # First time only
npm run dev
```

Open browser: **http://localhost:3000**

## 📂 Documentation

- **[INTEGRATION_ANALYSIS.md](frontend-demo/INTEGRATION_ANALYSIS.md)** - Detailed analysis of frontend/backend compatibility
- **[SETUP_GUIDE.md](frontend-demo/SETUP_GUIDE.md)** - Complete setup and testing guide
- **[IMPLEMENTATION_SUMMARY.md](frontend-demo/IMPLEMENTATION_SUMMARY.md)** - What was implemented and how it works

## ✨ Key Features

1. **2D Visualization** - UMAP projection of behavior embeddings
2. **Real-time Analysis** - Fetch user profiles from MongoDB
3. **Threshold Tuning** - Interactive cluster re-classification
4. **LLM Context** - Inject CORE behaviors into chat prompts
5. **Dynamic Users** - Load users from database

## 🎯 What's New

### Backend APIs
- `GET /api/v1/profile/{user_id}/analysis-summary` - Dashboard with 2D projections
- `POST /api/v1/profile/{user_id}/simulate-threshold` - Threshold simulation
- Enhanced `/api/v1/profile/{user_id}/llm-context` - Context for LLM

### Frontend
- Replaced all mock data with real API calls
- Added API service layer ([api.ts](frontend-demo/api.ts))
- Integrated LLM context injection
- Dynamic user loading and switching

## 🧪 Testing

1. Navigate to Dashboard → Click "Run Analysis"
2. Go to "Embedding Space" → See 2D visualization
3. Open "Threshold Lab" → Move slider to see cluster changes
4. Try "Context-Aware Chat" → Test personalization

## 📊 Architecture

```
Frontend (React) ⟷ Backend (FastAPI) ⟷ MongoDB + Qdrant
  Port 3000           Port 8000            Databases
```

## 🔧 Troubleshooting

**"Loading users..." stuck?**
- Check backend is running: `http://localhost:8000/api/v1/health`

**"Failed to fetch analysis data"?**
- User needs a profile in MongoDB
- Run: `POST /api/v1/analyze-behaviors-from-storage?user_id=user_665390`

**Points in a circle (2D viz)?**
- Install UMAP: `pip install umap-learn`

See [SETUP_GUIDE.md](frontend-demo/SETUP_GUIDE.md) for more troubleshooting.

## 📝 Notes

- **No authentication required** (as specified)
- Works with existing user data
- All CORE functionality implemented
- Ready for testing and demo

## 🎉 Status

✅ Backend APIs implemented  
✅ Frontend integrated  
✅ 2D visualization working  
✅ LLM context injection ready  
✅ Documentation complete  

**Ready for deployment and testing!**
