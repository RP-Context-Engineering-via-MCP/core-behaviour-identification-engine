# Running CBIE API Locally (Manual Setup)

This guide provides the steps to start the **Core Behaviour Identification Engine (CBIE)** API service manually on your local machine without using Docker.

## Prerequisites

- **Python 3.10+** installed.
- Access to the `.env` file with necessary credentials (Supabase, OpenAI/Azure, etc.).

## Step-by-Step Local Setup

Follow these steps exactly to get the API running on your machine:

### Step 1: Open Terminal in Root Directory
Open your terminal (PowerShell or Command Prompt) and navigate to the project root:
```powershell
cd d:\Academics\impl-final\cbie_engine
```

### Step 2: Set Up Virtual Environment
Create a clean environment and activate it to avoid package conflicts:
```powershell
# Create the environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
Install the lightweight API-specific requirements:
```powershell
pip install -r requirements_api.txt
```

### Step 4: Verify Environment Variables
Ensure you have a `.env` file in the root directory (`cbie_engine/`) with:
- `SUPABASE_URL` & `SUPABASE_KEY`
- `BAC_SUPABASE_URL` & `BAC_SUPABASE_KEY`
- `OPENAI_API_KEY` or Azure OpenAI configs.

### Step 5: Launch the Server
Start the Uvicorn server. We use `--reload` so it restarts automatically if you change the code:
```powershell
uvicorn api.main:app --host 0.0.0.0 --port 6009 --reload
```

### Step 6: Wait for Model Initialization
The first time you start, look for these log lines:
1. `Zero-Shot Classifier loaded` (BART Model)
2. `spaCy model loaded with EntityRuler`
3. `All resources ready — accepting requests`

Once you see these, the API is fully live at `http://localhost:6009`.

## API Documentation
Once the server is running and the "All resources ready" message appears in the logs, you can access the interactive documentation:

- **Swagger UI:** [http://localhost:6009/docs](http://localhost:6009/docs)
- **ReDoc:** [http://localhost:6009/redoc](http://localhost:6009/redoc)

## Troubleshooting
- **ModuleNotFoundError:** Ensure you are running the `uvicorn` command from the root `cbie_engine` folder so that internal imports resolve correctly.
- **Port Conflict:** If port `6009` is in use, change the `--port` argument in the startup command.
