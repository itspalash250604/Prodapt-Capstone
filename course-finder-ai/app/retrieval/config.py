"""Shared retrieval configuration."""

from __future__ import annotations

from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CLEAN_COURSES_PATH = DATA_DIR / "clean_courses.csv"
CHROMA_DIR = DATA_DIR / "chroma"

SEMANTIC_COLLECTION_NAME = "course_semantic_index"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE = 64

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"
RERANKER_MAX_LENGTH = 512

# Optional caching for repeated retrieval queries.
CACHE_TTL_SECONDS = int(os.getenv("COURSE_SEARCH_CACHE_TTL_SECONDS", "3600"))
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_KEY_PREFIX = os.getenv("COURSE_SEARCH_CACHE_PREFIX", "course_search")
