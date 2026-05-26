
# 🚀 Course Finder AI

An **AI-powered course recommendation platform** that helps learners discover the most relevant online courses based on their **career goals, existing skills, learning intent, and skill gaps**.

The system intelligently analyzes learner profiles, retrieves semantically relevant courses, evaluates career alignment, and generates personalized learning guidance.

---

## ✨ Features

✅ **Personalized Course Recommendations**  
Get course suggestions tailored to your goals, current skills, and learning objectives.

✅ **Skill Gap Analysis**  
Identifies missing skills required to achieve a target career path.

✅ **Semantic Course Retrieval**  
Uses vector search and embeddings to find the most relevant courses.

✅ **AI-Powered Recommendation Workflow**  
Evaluates:
- Career alignment
- Skill gaps
- Learning readiness
- Guardrails & recommendation quality
- Learning path progression

✅ **Learning Path Guidance**  
Provides preparation advice and next-step recommendations.

✅ **Multi-Input Support**
- Text-based learner queries
- PDF profile/document upload
- Audio input transcription

✅ **Interactive Frontend**
Modern React UI for end-to-end interaction.

---

## 🏗️ Tech Stack

### Backend
- **FastAPI** – API framework
- **LangGraph** – Multi-step recommendation workflow
- **Sentence Transformers** – Embedding generation
- **ChromaDB** – Vector database for semantic retrieval
- **Python** – Core backend logic

### Frontend
- **React (Vite)** – User interface
- **JavaScript** – Frontend logic

### AI / NLP
- **Semantic Search**
- **Vector Embeddings**
- **Skill Gap Analysis**
- **Learning Path Generation**

---

## 📂 Project Structure

```
course-finder-ai/
│── app/                  # FastAPI backend, agents, workflows
│── data/                 # Dataset and ChromaDB index
│── react_frontend/       # React + Vite frontend
│── scripts/              # Utility scripts
│── tests/                # Automated tests
│── requirements.txt
│── README.md
```
### Folder Overview

| Folder            | Description                                                                        |
| ----------------- | ---------------------------------------------------------------------------------- |
| `app/`            | Backend APIs, LangGraph workflow, retrieval system, guardrails, skill-gap analysis |
| `data/`           | Course dataset and vector index                                                    |
| `react_frontend/` | Frontend built using React + Vite                                                  |
| `scripts/`        | Data preprocessing, indexing, evaluation scripts                                   |
| `tests/`          | Backend unit and integration tests                                                 |

---

## ⚙️ Requirements

Before running the project, make sure you have:

* **Python 3.10+**
* **Node.js 18+**
* **npm**

---

# 🛠️ Installation & Setup

## 1️⃣ Clone the Repository

```powershell
git clone <your-repo-url>
cd course-finder-ai
```

---

## 2️⃣ Create a Virtual Environment

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### PowerShell Execution Policy Fix

If PowerShell blocks script execution:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

---

## 3️⃣ Install Backend Dependencies

```powershell
pip install -r requirements.txt
```

---

## 4️⃣ Install Frontend Dependencies

```powershell
cd react_frontend
npm install
```

---

# ▶️ Running The Application

You will need **two terminals** running simultaneously.

---

## Terminal 1 — Backend

From the project root:

```powershell
uvicorn app.main:app --reload
```

The backend may take some time to initialize while loading:

* Embedding models
* Retrieval components
* Workflow services

Backend runs at:

```txt
http://127.0.0.1:8000
```

---

## Terminal 2 — Frontend

Navigate to the frontend directory:

```powershell
cd react_frontend
npm run dev
```

Vite will provide a local URL such as:

```txt
http://localhost:5173
```

Open it in your browser to use the application.

---

# 🔌 API Endpoints

Base route:

```txt
/api/v1
```

| Method | Endpoint           | Description                         |
| ------ | ------------------ | ----------------------------------- |
| `GET`  | `/health`          | Health check                        |
| `POST` | `/intake/pdf`      | Upload and normalize PDF profile    |
| `POST` | `/intake/audio`    | Upload and transcribe audio         |
| `POST` | `/recommendations` | Generate AI-powered recommendations |

---

## 📘 API Documentation

Once the backend is running, interactive API docs are available at:

```txt
http://127.0.0.1:8000/docs
```

---

# ⚡ Retrieval Cache (Optional)

Semantic search supports query caching for faster repeated recommendations.

### Recommended Environment Variables

```bash
REDIS_URL=redis://localhost:6379/0
COURSE_SEARCH_CACHE_TTL_SECONDS=3600
COURSE_SEARCH_CACHE_PREFIX=course_search
```

### Cache Behavior

* Uses **Redis** if available
* Falls back to **in-memory caching** automatically
* Cache keys include:

  * query
  * top_k
  * filters
  * collection name
  * embedding model

---

# 🧪 Useful Commands

### Run Backend Tests

```powershell
venv\Scripts\python.exe -m pytest
```

### Build Frontend

```powershell
cd react_frontend
npm run build
```

---

# 🐞 Troubleshooting

### Python Import Errors

Ensure the virtual environment is activated:

```powershell
.\venv\Scripts\Activate.ps1
```

---

### Frontend Cannot Reach Backend

Verify:

* `uvicorn` is still running
* Backend is active on port `8000`

---

### Slow Model Loading

The first startup may take longer because:

* Embedding models are loading
* Vector retrieval systems are initializing

Please wait a few moments after starting the backend.

---

# 🎯 How It Works

```txt
Learner Input
      ↓
Profile + Goal Analysis
      ↓
Skill Gap Detection
      ↓
Semantic Course Retrieval
      ↓
AI Recommendation Workflow
      ↓
Reranking & Validation
      ↓
Personalized Course Suggestions
      ↓
Learning Path Guidance
```

---

# 🤝 Contributing

Contributions, improvements, and suggestions are welcome.

Feel free to fork the repository and submit a pull request.

---

# 📄 License

This project is licensed under the **MIT License**.



### What improved?
- Better **GitHub visual appeal**
- Cleaner **section hierarchy**
- More professional formatting
- Added **feature highlights**
- Better **tech stack presentation**
- Added **workflow diagram**
- Better **table formatting**
- More readable setup instructions
- Cleaner **API documentation**
- Professional **open-source feel**

This version will look much more polished on GitHub and closer to production-grade repositories recruiters or internship evaluators expect to see.
    
