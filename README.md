# Core Behavior Identification Engine (CBIE)

A sophisticated system for identifying, clustering, and analyzing user behavior patterns using machine learning and vector embeddings.

## Architecture

CBIE uses a **cluster-centric architecture** that groups semantically similar behavior observations into meaningful clusters. The system leverages:

- **HDBSCAN clustering** for automatic pattern detection
- **Vector embeddings** (OpenAI) for semantic similarity
- **MongoDB** for behavior storage
- **Qdrant** for efficient vector search
- **Multi-tier classification** (PRIMARY, SECONDARY, NOISE)

## Features

- ✅ Behavior observation ingestion
- ✅ Automatic clustering using HDBSCAN
- ✅ Cluster strength and confidence scoring
- ✅ Temporal decay and recency tracking
- ✅ User archetype generation
- ✅ LLM context injection for personalization
- ✅ RESTful API with FastAPI

## Installation

### Prerequisites

- Python 3.10+
- MongoDB
- Qdrant
- OpenAI API key

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd core-behaviour-identification-engine
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=behavior_db
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your_api_key_here

# Optional tuning parameters
ALPHA=0.35
BETA=0.40
GAMMA=0.25
MIN_CLUSTER_SIZE=3
PRIMARY_THRESHOLD=0.70
SECONDARY_THRESHOLD=0.50
```

## Quick Start

### Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

This will start:
- MongoDB on port 27017
- Qdrant on port 6333
- API service on port 8000

### Manual Start

1. Start MongoDB:
```bash
mongod
```

2. Start Qdrant:
```bash
docker run -p 6333:6333 qdrant/qdrant:v1.7.0
```

3. Run the API:
```bash
uvicorn main:app --reload
```

## API Usage

### Health Check
```bash
curl http://localhost:8000/
```

### Create Behavior Observation
```bash
curl -X POST http://localhost:8000/behaviors \
  -H "Content-Type: application/json" \
  -d '{
    "behavior_text": "User prefers dark mode interfaces",
    "credibility": 0.95,
    "clarity_score": 0.90,
    "extraction_confidence": 0.85
  }'
```

### Analyze Clusters
```bash
curl -X POST http://localhost:8000/clusters/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "observation_ids": ["obs_1", "obs_2", "obs_3"]
  }'
```

## System Architecture

```
User Behaviors → Embeddings → Clustering → Cluster Scoring → Archetypes
                     ↓
                 MongoDB                      Qdrant
              (Observations)            (Vector Search)
```

### Key Components

1. **Calculation Engine**: BW, ABW, cluster strength, confidence scoring
2. **Clustering Engine**: HDBSCAN-based behavior grouping
3. **Cluster Analysis Pipeline**: End-to-end processing
4. **Archetype Service**: User pattern summarization
5. **LLM Context Service**: Behavior data formatting for AI

## Configuration

Tunable parameters in `src/config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `alpha` | 0.35 | Credibility weight |
| `beta` | 0.40 | Clarity weight |
| `gamma` | 0.25 | Extraction confidence weight |
| `min_cluster_size` | 3 | Minimum observations per cluster |
| `primary_threshold` | 0.70 | PRIMARY tier threshold |
| `secondary_threshold` | 0.50 | SECONDARY tier threshold |

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Development History

This project evolved through several architectural phases:

1. **October 2025**: Foundation (FastAPI, MongoDB, basic models)
2. **Early November 2025**: Observation-centric pipeline
3. **Late November 2025**: Architecture pivot to cluster-centric approach
4. **December 2025**: Refinement, testing, documentation

## License

MIT License

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
