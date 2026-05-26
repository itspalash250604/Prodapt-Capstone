
```markdown
# 🎓 Course Finder AI

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-🦜🔗-blue?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

Course Finder AI is an intelligent, multi-modal course recommendation system designed to help learners discover relevant online education based on their unique professional profiles, career goals, and immediate skill gaps. 

By leveraging semantic search, graph-based agentic workflows, and multi-modal intake pipelines, the system processes user context, evaluates skill deficiencies, maps out customized learning paths, and delivers highly tailored, ranked course recommendations complete with strategic logic and preparation guidance.

---

## 🚀 Key Features

* **Multi-Modal Profile Intake:** Accept learner contexts via raw text queries, parsed resume PDFs, or transcribed audio inputs.
* **Semantic Retrieval & Reranking:** Utilize Sentence Transformers and ChromaDB to fetch deep contextually matched courses beyond simple keyword matching.
* **Agentic Evaluation Workflow:** Powered by **LangGraph** to seamlessly handle career alignment checks, skill-gap analysis, guardrail filtering, and learning-path generation.
* **Hybrid Caching Layer:** In-memory caching with seamless, automatic fallback to Redis for high-throughput production environments.
* **Interactive UI:** Modern React + Vite frontend for a smooth, end-to-end interactive user experience.

---

## 📁 Repository Layout

```text
course-finder-ai/
├── app/                  # FastAPI backend (Agents, retrieval, guardrails, workflows)
├── data/                 # Course datasets and local ChromaDB vector index files
├── react_frontend/       # Frontend UI (Vite + React.js SPA)
├── scripts/              # Data preprocessing, indexing, and evaluation utilities
└── tests/                # Robust PyTest suite for backend workflows and modules

```

---

## 🛠️ Tech Stack & Requirements

* **Backend:** Python 3.10+ | FastAPI | LangGraph | LangChain | Sentence Transformers | ChromaDB
* **Frontend:** Node.js 18+ | React | Vite
* **Caching (Optional):** Redis

---

## ⚙️ Setup & Installation

Follow these steps to get your local development environment up and running.

### 1. Clone the Repository

```bash
git clone [https://github.com/your-username/course-finder-ai.git](https://github.com/your-username/course-finder-ai.git)
cd course-finder-ai

```

### 2. Backend Environment Setup

Create and activate a virtual environment, then install the required Python dependencies:

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# (Optional) If PowerShell blocks script execution, run:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Install backend dependencies
pip install -r requirements.txt

```

### 3. Frontend Environment Setup

Navigate to the frontend directory and install the Node packages:

```bash
cd react_frontend
npm install

```

---

## 🏃 Running the Application

To run the full stack application, open **two separate terminal windows**:

### Terminal 1: FastAPI Backend

From the root directory (`course-finder-ai/`):

```bash
uvicorn app.main:app --reload

```

> *Note: The first execution might take a moment as embedding models and semantic indices initialize into memory.*

### Terminal 2: React Frontend

From the frontend directory (`course-finder-ai/react_frontend`):

```bash
npm run dev

```

Once both services are running, open the local server URL provided by Vite in your browser.

---

## 🔌 Backend API Reference

The FastAPI application exposes structured, versioned routes under `/api/v1`.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/v1/health` | `GET` | Core service health check |
| `/api/v1/intake/pdf` | `POST` | Upload and normalize a PDF profile/resume |
| `/api/v1/intake/audio` | `POST` | Upload and transcribe audio query inputs |
| `/api/v1/recommendations` | `POST` | Orchestrate LangGraph workflow to generate ranked recommendations |

### 📖 Interactive Documentation

When the backend server is active, access the fully interactive Swagger documentation UI at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## ⚡ Optional Retrieval Caching

Semantic course search supports caching to speed up recurring queries. By default, the system boots with an **in-memory cache**, but automatically scales to **Redis** if a `REDIS_URL` is detected in your environment.

### Recommended Environment Configuration

Create a `.env` file in your root folder:

```env
REDIS_URL=redis://localhost:6379/0
COURSE_SEARCH_CACHE_TTL_SECONDS=3600
COURSE_SEARCH_CACHE_PREFIX=course_search

```

> **How it works:** Cached entries are uniquely keyed by a cryptographic combination of the user text query, `top_k` limit, structural metadata filters, database collection name, and active embedding model.

---

## 🔧 Useful Commands

```powershell
# Run the automated backend test suite
venv\Scripts\python.exe -m pytest

# Build the React frontend for production deployment
cd react_frontend
npm run build

```

---

## 🔍 Troubleshooting

* **ModuleNotFoundError / Missing Packages:** Ensure your virtual environment (`venv`) is fully activated in your current terminal workspace before launching `uvicorn`.
* **Network Connection Refused:** If the React UI cannot connect to the backend, verify that `uvicorn` is active and explicitly listening on `port 8000`.
* **Slow Startup Latency:** If the backend appears hanging on the first run, please do not close the process. It is downloading the local Sentence Transformer embedding weights from HuggingFace. Subsequent startups will be instant.

```

```
