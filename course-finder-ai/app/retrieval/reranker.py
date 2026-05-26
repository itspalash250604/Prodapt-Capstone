"""Cross-encoder reranking for retrieved course candidates."""

from __future__ import annotations

from collections.abc import Sequence

from sentence_transformers import CrossEncoder

from app.retrieval.config import RERANKER_MAX_LENGTH, RERANKER_MODEL_NAME
from app.retrieval.models import CourseSearchResult


class CrossEncoderCourseReranker:
    """Rerank candidate courses by direct query-course relevance scoring.

    The retriever's job is to quickly find a candidate set. The reranker's job is
    to judge those candidates more carefully by reading the query and course text
    together.
    """

    def __init__(
        self,
        model_name: str = RERANKER_MODEL_NAME,
        max_length: int = RERANKER_MAX_LENGTH,
    ) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._model: CrossEncoder | None = None

    def rerank(
        self,
        query: str,
        candidates: Sequence[CourseSearchResult],
        top_k: int | None = None,
    ) -> list[CourseSearchResult]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k is not None and top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if not candidates:
            return []

        pairs = [
            (query, self._candidate_text(candidate))
            for candidate in candidates
        ]
        scores = self.model.predict(pairs).tolist()

        reranked = [
            self._with_rerank_score(candidate, float(score))
            for candidate, score in zip(candidates, scores)
        ]
        reranked.sort(key=lambda result: result.score, reverse=True)

        if top_k is None:
            return reranked
        return reranked[:top_k]

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                local_files_only=True,
            )
        return self._model

    @staticmethod
    def _candidate_text(candidate: CourseSearchResult) -> str:
        metadata = candidate.metadata
        fields = [
            f"Title: {candidate.title}",
            f"Provider: {candidate.organization}",
            f"Difficulty: {metadata.get('difficulty', '')}",
            f"Type: {metadata.get('course_type', '')}",
            f"Duration: {metadata.get('duration', '')}",
            f"Skills: {metadata.get('skills_text', '')}",
        ]

        document = candidate.document.strip()
        if document:
            fields.append(f"Course text: {document}")

        return "\n".join(field for field in fields if not field.endswith(": "))

    @staticmethod
    def _with_rerank_score(
        candidate: CourseSearchResult,
        rerank_score: float,
    ) -> CourseSearchResult:
        metadata = dict(candidate.metadata)
        metadata["semantic_score"] = candidate.score
        metadata["rerank_score"] = rerank_score

        return CourseSearchResult(
            course_id=candidate.course_id,
            title=candidate.title,
            organization=candidate.organization,
            score=rerank_score,
            metadata=metadata,
            document=candidate.document,
        )
