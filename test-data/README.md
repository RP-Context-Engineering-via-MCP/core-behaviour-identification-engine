# Test Data for CBIE System

This directory contains synthetic test datasets for evaluating the Core Behavior Identification Engine (CBIE).

## 📁 Directory Structure

```
test-data/
├── gen_data.py                          # Data generation script
├── README.md                            # This file
└── realistic_evaluation_set/
    ├── dataset_summary.json             # Overview of all datasets
    ├── behaviors_user_*.json            # User behavior files
    └── prompts_user_*.json              # User prompt files
```

## 🎯 Available Test Datasets

### 1. **user_small_dataset**
- **Description:** Small dataset - few behaviors, low activity
- **Characteristics:**
  - 8 behaviors
  - 79 prompts
  - 10% noise ratio
  - 15-day timespan
- **Use Case:** Testing basic functionality, quick validation

### 2. **user_medium_clear**
- **Description:** Medium dataset - clear patterns, low noise
- **Characteristics:**
  - 12 behaviors
  - 320 prompts
  - 8% noise ratio (very clean)
  - 30-day timespan
- **Use Case:** Ideal for demonstrating clear clustering results

### 3. **user_large_diverse**
- **Description:** Large dataset - diverse behaviors, higher noise
- **Characteristics:**
  - 18 behaviors
  - 637 prompts
  - 20% noise ratio
  - 60-day timespan
- **Use Case:** Testing scalability and noise handling

### 4. **user_noisy_explorer**
- **Description:** Exploratory user - many unrelated queries
- **Characteristics:**
  - 10 behaviors
  - 187 prompts
  - 35% noise ratio (very noisy)
  - 45-day timespan
- **Use Case:** Testing INSUFFICIENT_EVIDENCE classification

### 5. **user_focused_specialist**
- **Description:** Focused specialist - few but very strong behaviors
- **Characteristics:**
  - 5 behaviors (few but strong)
  - 284 prompts
  - 5% noise ratio (very focused)
  - 90-day timespan
- **Use Case:** Testing strong CORE behavior identification

## 🔧 Generating New Datasets

To generate new test datasets:

```bash
cd test-data
python gen_data.py
```

### Customization

Edit the `USER_PROFILES` configuration in `gen_data.py`:

```python
USER_PROFILES = [
    {
        "user_id": "your_user_id",
        "num_behaviors": 10,        # Number of distinct behaviors
        "min_prompts": 15,          # Min prompts per behavior
        "max_prompts": 40,          # Max prompts per behavior
        "noise_ratio": 0.15,        # 15% noise prompts
        "days_back": 30,            # Time span in days
        "description": "Your description"
    }
]
```

## 📊 Behavior Archetypes

The generator includes 11 distinct behavior patterns:

| Category | Behavior Description |
|----------|---------------------|
| `visual` | Prefers visual diagrams and flowcharts |
| `code` | Requests code examples and snippets |
| `step` | Prefers step-by-step instructions |
| `debug` | Focuses on debugging and troubleshooting |
| `concise` | Prefers concise, brief explanations |
| `deep` | Requests detailed, comprehensive explanations |
| `security` | Frequently asks about security vulnerabilities |
| `perf` | Focuses on performance optimization |
| `theory` | Prefers theoretical concepts over implementation |
| `compare` | Asks for comparisons between technologies |
| `best_practice` | Requests best practices and standards |

## 🚀 Using Test Data

### Option 1: Load via API (Recommended)

```bash
# Start the backend server
cd project
python main.py

# Use the test data upload endpoint
curl -X POST http://localhost:8000/api/v1/test/upload \
  -H "Content-Type: application/json" \
  -d @test-data/realistic_evaluation_set/behaviors_user_medium_clear.json
```

### Option 2: Direct MongoDB Import

```python
from src.database.mongodb_service import mongodb_service
import json

# Load data
with open("test-data/realistic_evaluation_set/behaviors_user_medium_clear.json") as f:
    behaviors = json.load(f)
with open("test-data/realistic_evaluation_set/prompts_user_medium_clear.json") as f:
    prompts = json.load(f)

# Insert into MongoDB
mongodb_service.db.behaviors.insert_many(behaviors)
mongodb_service.db.prompts.insert_many(prompts)
```

### Option 3: Frontend Demo Integration

The test datasets are designed to work with the frontend demo visualization:

1. Load data using Option 1 or 2
2. Navigate to `http://localhost:3001` (frontend demo)
3. Select user from dropdown
4. View clustering results with 2D embedding space

## 📈 Expected Analysis Results

### user_medium_clear (Recommended for Demo)
- **Expected:** 2-4 CORE clusters with high stability (>0.5)
- **Expected:** 1-2 INSUFFICIENT_EVIDENCE clusters
- **Expected:** Minimal NOISE behaviors
- **Visualization:** Clear, well-separated clusters in 2D space

### user_focused_specialist
- **Expected:** 1-2 CORE clusters with very high stability (>0.7)
- **Expected:** Long temporal spans (90 days)
- **Expected:** High reinforcement counts (30-80 prompts)

### user_noisy_explorer
- **Expected:** More INSUFFICIENT_EVIDENCE and NOISE classifications
- **Expected:** Lower average stability scores
- **Expected:** Many singleton or small clusters

## 🔍 Data Validation

Each generated dataset includes:

✅ **Realistic timestamps** - Spread over specified time period  
✅ **Linked prompt histories** - Each behavior references its source prompts  
✅ **Varied reinforcement** - Different prompt counts per behavior  
✅ **Session tracking** - Prompts grouped by session IDs  
✅ **Noise prompts** - Unlinked prompts to test NOISE handling  
✅ **Credibility scores** - Based on reinforcement count  

## 📝 Notes

- All timestamps are in Unix epoch format
- Prompt IDs are hex-based: `prompt_a3f8e2`
- Behavior IDs format: `beh_9c1d4f`
- Observation IDs format: `obs_7e2a93`
- Session IDs format: `sess_{category}_{index}`

## 🎓 Generated: January 4, 2026

These datasets were generated using the enhanced `gen_data.py` script with configurable user profiles for comprehensive system testing.
