"""Semantic course retrieval backed by Sentence Transformers and ChromaDB."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
from dataclasses import asdict

import chromadb
import pandas as pd
from chromadb.api.models.Collection import Collection
from chromadb.errors import NotFoundError
from sentence_transformers import SentenceTransformer

from app.retrieval.config import (
    CACHE_TTL_SECONDS,
    CHROMA_DIR,
    CLEAN_COURSES_PATH,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    SEMANTIC_COLLECTION_NAME,
    REDIS_KEY_PREFIX,
)
from app.retrieval.cache import build_search_cache_key, create_retrieval_cache
from app.retrieval.models import CourseSearchResult


INDEX_METADATA_COLUMNS = [
    "title",
    "organization",
    "course_url",
    "difficulty",
    "difficulty_level",
    "course_type",
    "duration",
    "rating",
    "review_count",
    "students_enrolled",
    "skills_text",
    "skill_count",
    "description_status",
    "has_url",
    "has_description",
    "has_enrollment",
]


def _clean_metadata_value(value: Any) -> str | int | float | bool:
    """Convert pandas values into Chroma-compatible scalar metadata."""
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float | str):
        return value
    return str(value)


def _records_in_batches(records: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def _normalize_filters(filters: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert simple equality filters into Chroma's expected where syntax."""
    if not filters:
        return None
    if len(filters) == 1:
        return filters
    return {"$and": [{key: value} for key, value in filters.items()]}


class SemanticCourseIndexer:
    """Creates and refreshes the persistent Chroma semantic index."""

    def __init__(
        self,
        dataset_path: Path = CLEAN_COURSES_PATH,
        persist_dir: Path = CHROMA_DIR,
        collection_name: str = SEMANTIC_COLLECTION_NAME,
        model_name: str = EMBEDDING_MODEL_NAME,
        batch_size: int = EMBEDDING_BATCH_SIZE,
    ) -> None:
        self.dataset_path = dataset_path
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.model_name = model_name
        self.batch_size = batch_size

    def build(self, recreate: bool = True) -> int:
        courses = self._load_courses()
        model = SentenceTransformer(self.model_name, local_files_only=True)
        client = chromadb.PersistentClient(path=str(self.persist_dir))

        if recreate:
            try:
                client.delete_collection(self.collection_name)
            except (ValueError, NotFoundError):
                pass

        collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description": "Semantic course retrieval index",
                "embedding_model": self.model_name,
            },
        )

        records = courses.to_dict(orient="records")
        for batch in _records_in_batches(records, self.batch_size):
            documents = [record["embedding_text"] for record in batch]
            embeddings = model.encode(
                documents,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            collection.add(
                ids=[record["course_id"] for record in batch],
                documents=documents,
                embeddings=embeddings,
                metadatas=[self._metadata_from_record(record) for record in batch],
            )

        return collection.count()

    def _load_courses(self) -> pd.DataFrame:
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Clean dataset not found at {self.dataset_path}. "
                "Run scripts/preprocess_courses.py first."
            )

        courses = pd.read_csv(self.dataset_path)
        required_columns = {"course_id", "embedding_text", *INDEX_METADATA_COLUMNS}
        missing_columns = required_columns - set(courses.columns)
        if missing_columns:
            raise ValueError(f"Clean dataset is missing columns: {sorted(missing_columns)}")

        empty_embeddings = courses["embedding_text"].fillna("").astype(str).str.strip().eq("")
        if empty_embeddings.any():
            raise ValueError(f"Found {int(empty_embeddings.sum())} rows with empty embedding_text")

        if courses["course_id"].duplicated().any():
            raise ValueError("course_id values must be unique before indexing")

        return courses

    @staticmethod
    def _metadata_from_record(record: dict[str, Any]) -> dict[str, str | int | float | bool]:
        return {
            column: _clean_metadata_value(record.get(column, ""))
            for column in INDEX_METADATA_COLUMNS
        }


class SemanticCourseRetriever:
    """Queries the Chroma semantic index using a sentence-transformer query vector."""

    def __init__(
        self,
        persist_dir: Path = CHROMA_DIR,
        collection_name: str = SEMANTIC_COLLECTION_NAME,
        model_name: str = EMBEDDING_MODEL_NAME,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.model_name = model_name
        self.cache_ttl_seconds = cache_ttl_seconds
        self._model: SentenceTransformer | None = None
        self._collection: Collection | None = None
        self._cache = create_retrieval_cache(ttl_seconds=cache_ttl_seconds, prefix=REDIS_KEY_PREFIX)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[CourseSearchResult]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        cache_key = build_search_cache_key(
            query=query,
            top_k=top_k,
            filters=filters,
            collection_name=self.collection_name,
            model_name=self.model_name,
        )
        cached_results = self._cache.get(cache_key)
        if cached_results is not None:
            return [CourseSearchResult(**item) for item in cached_results]

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0].tolist()

        raw_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=_normalize_filters(filters),
            include=["documents", "metadatas", "distances"],
        )

        results = self._to_search_results(raw_results)
        self._cache.set(cache_key, [asdict(result) for result in results])
        return results

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, local_files_only=True)
        return self._model

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = client.get_collection(self.collection_name)
        return self._collection

    @staticmethod
    def _to_search_results(raw_results: dict[str, Any]) -> list[CourseSearchResult]:
        ids = raw_results.get("ids", [[]])[0]
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        results: list[CourseSearchResult] = []
        for course_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            score = 1.0 / (1.0 + float(distance))
            results.append(
                CourseSearchResult(
                    course_id=course_id,
                    title=str(metadata.get("title", "")),
                    organization=str(metadata.get("organization", "")),
                    score=score,
                    metadata=dict(metadata),
                    document=str(document),
                )
            )

        return results
