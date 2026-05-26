# Course Finder AI

Course Finder AI is an AI-powered course recommendation system that helps a learner discover relevant online courses based on their profile, goals, and skill gaps. The backend analyzes the input, retrieves matching courses from a semantic index, optionally reranks the results, and then enriches the recommendations with supporting details such as rationale, preparation guidance, and learning-path notes. The React frontend provides the user interface for trying the system end to end.

## What This Project Does

At a high level, the app:

1. Accepts a learner query and related profile information.
2. Retrieves semantically similar courses from the indexed dataset.
3. Uses a recommendation workflow to evaluate career alignment, skill gaps, guardrails, and a learning path.
4. Returns ranked course suggestions with explanations and next-step guidance.

The project is built around FastAPI, LangGraph, Sentence Transformers, ChromaDB, and a React frontend.

## Repository Layout

- `app/` - FastAPI backend, agents, retrieval, guardrails, skill-gap analysis, and learning-path logic.
- `data/` - Course dataset and ChromaDB index files.
- `react_frontend/` - Vite + React frontend.
- `scripts/` - Utility scripts for preprocessing, indexing, evaluation, and analysis.
- `tests/` - Automated tests for the backend workflow and supporting modules.

## Requirements

- Python 3.10+ recommended
- Node.js 18+ recommended
- npm

## Setup

### 1. Create and activate a virtual environment

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install frontend dependencies

```powershell
cd react_frontend
npm install
```

## How To Run The App

You need two terminals: one for the backend and one for the frontend.

### Backend

Open a terminal in the project root `course-finder-ai/` and run:

```powershell
uvicorn app.main:app --reload
```

The backend will start once the models and services finish loading.

### Frontend

Open a second terminal and go to `course-finder-ai/react_frontend`, then run:

```powershell
npm run dev
```

After both services are running, open the local URL shown by Vite in your browser and use the app normally.

## Backend API

The FastAPI app exposes its routes under `/api/v1`.

- `GET /api/v1/health` - health check
- `POST /api/v1/intake/pdf` - upload and normalize a PDF profile or document
- `POST /api/v1/intake/audio` - upload and transcribe audio input
- `POST /api/v1/recommendations` - generate course recommendations

When the backend is running, interactive API docs are available at:

- `http://127.0.0.1:8000/docs`

## Optional Retrieval Cache

Semantic course search supports caching repeated queries. By default it uses an in-memory cache, and it can switch to Redis when `REDIS_URL` is set.

Recommended environment variables:

```bash
REDIS_URL=redis://localhost:6379/0
COURSE_SEARCH_CACHE_TTL_SECONDS=3600
COURSE_SEARCH_CACHE_PREFIX=course_search
```

Notes:

- If Redis is available, it will be used for shared cache storage.
- If Redis is unavailable, the app falls back to an in-memory cache automatically.
- Cached entries are keyed by the query, `top_k`, filters, collection name, and embedding model name.

## Useful Commands

```powershell
# Run backend tests
venv\Scripts\python.exe -m pytest

# Build the React frontend
cd react_frontend
npm run build
```

## Troubleshooting

- If Python packages fail to import, make sure the virtual environment is activated before starting the backend.
- If the frontend cannot reach the backend, confirm that `uvicorn` is still running and that the backend is listening on port `8000`.
- If model loading is slow on the first run, wait a little longer after starting the backend. The app may need extra time to initialize embeddings and retrieval components.
