"""Sentence-aware semantic chunking for conversational transcripts."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

import numpy as np

from app.nlp_preprocessing.embedding_service import EmbeddingService, get_embedding_service


logger = logging.getLogger(__name__)

CLAUSE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|(?<=,)\s+|\n+")
CONTINUATION_PREFIXES = (
    "and ",
    "also ",
    "currently ",
    "plus ",
    "so ",
    "because ",
    "but ",
    "while ",
    "then ",
    "i also ",
    "i'm also ",
    "im also ",
)


@dataclass(frozen=True)
class SemanticChunk:
    """One semantically coherent chunk of transcript text."""

    text: str
    clause_count: int
    coherence: float


class SemanticChunker:
    """Groups related transcript clauses into semantic chunks."""

    def __init__(self, embedding_service: EmbeddingService | None = None, similarity_threshold: float = 0.42) -> None:
        self.embedding_service = embedding_service or get_embedding_service()
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str) -> list[SemanticChunk]:
        normalized = text.strip()
        if not normalized:
            return []

        clauses = [clause.strip() for clause in CLAUSE_SPLIT_RE.split(normalized) if clause and clause.strip()]
        if len(clauses) <= 1:
            return [SemanticChunk(text=normalized, clause_count=1, coherence=1.0)]

        try:
            embeddings = self.embedding_service.embed_texts(clauses)
            return self._chunk_with_embeddings(clauses, embeddings)
        except Exception:
            logger.info("Falling back to clause grouping without embeddings")
            return self._chunk_without_embeddings(clauses)

    def _chunk_with_embeddings(self, clauses: list[str], embeddings: np.ndarray) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        current_clauses = [clauses[0]]
        current_vectors = [embeddings[0]]

        for index in range(1, len(clauses)):
            clause = clauses[index]
            vector = embeddings[index]
            similarity = self.embedding_service.cosine_similarity(current_vectors[-1], vector)
            should_merge = self._should_merge(clause, similarity, current_clauses)

            if should_merge:
                current_clauses.append(clause)
                current_vectors.append(vector)
                continue

            chunks.append(self._build_chunk(current_clauses, current_vectors))
            current_clauses = [clause]
            current_vectors = [vector]

        chunks.append(self._build_chunk(current_clauses, current_vectors))
        return chunks

    def _chunk_without_embeddings(self, clauses: list[str]) -> list[SemanticChunk]:
        chunks: list[SemanticChunk] = []
        current_clauses = [clauses[0]]

        for clause in clauses[1:]:
            if self._is_continuation(clause):
                current_clauses.append(clause)
                continue
            chunks.append(SemanticChunk(text=" ".join(current_clauses).strip(), clause_count=len(current_clauses), coherence=0.5))
            current_clauses = [clause]

        chunks.append(SemanticChunk(text=" ".join(current_clauses).strip(), clause_count=len(current_clauses), coherence=0.5))
        return chunks

    def _build_chunk(self, clauses: list[str], vectors: list[np.ndarray]) -> SemanticChunk:
        text = " ".join(clauses).strip()
        if len(vectors) <= 1:
            coherence = 1.0
        else:
            similarities = [self.embedding_service.cosine_similarity(vectors[i - 1], vectors[i]) for i in range(1, len(vectors))]
            coherence = float(sum(similarities) / len(similarities)) if similarities else 1.0
        return SemanticChunk(text=text, clause_count=len(clauses), coherence=coherence)

    def _should_merge(self, clause: str, similarity: float, current_clauses: list[str]) -> bool:
        if self._is_continuation(clause):
            return True
        if len(" ".join(current_clauses)) < 240:
            return similarity >= self.similarity_threshold - 0.08
        return similarity >= self.similarity_threshold

    @staticmethod
    def _is_continuation(clause: str) -> bool:
        lowered = clause.lstrip().casefold()
        return lowered.startswith(CONTINUATION_PREFIXES)
