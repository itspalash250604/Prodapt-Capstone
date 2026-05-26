"""Build the ChromaDB semantic index from data/clean_courses.csv."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.config import CHROMA_DIR, EMBEDDING_MODEL_NAME, SEMANTIC_COLLECTION_NAME
from app.retrieval.semantic import SemanticCourseIndexer


def main() -> None:
    indexer = SemanticCourseIndexer()
    count = indexer.build(recreate=True)

    print("Semantic index created")
    print(f"Collection: {SEMANTIC_COLLECTION_NAME}")
    print(f"Model: {EMBEDDING_MODEL_NAME}")
    print(f"Persist directory: {CHROMA_DIR}")
    print(f"Indexed courses: {count}")


if __name__ == "__main__":
    main()
