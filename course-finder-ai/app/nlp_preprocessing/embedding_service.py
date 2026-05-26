"""Embedding helpers used by transcript preprocessing."""

from __future__ import annotations

from functools import lru_cache
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from app.retrieval.config import EMBEDDING_MODEL_NAME


logger = logging.getLogger(__name__)


class EmbeddingService:
    """Lazy wrapper around a SentenceTransformer model."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, local_files_only=True)
        return self._model

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        try:
            vectors = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Embedding model unavailable for preprocessing: %s", exc)
            raise

        return np.asarray(vectors, dtype=np.float32)

    @staticmethod
    def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
        if left.size == 0 or right.size == 0:
            return 0.0
        return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right) + 1e-12))


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return a shared embedding service instance."""

    return EmbeddingService()
