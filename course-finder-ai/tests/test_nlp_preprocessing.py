from __future__ import annotations

import unittest

import numpy as np

from app.nlp_preprocessing.profile_extractor import ProfileExtractor
from app.nlp_preprocessing.retrieval_context import prepare_retrieval_context
from app.nlp_preprocessing.semantic_chunker import SemanticChunker


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            lowered = text.casefold()
            if any(token in lowered for token in ("backend", "engineer", "developer")):
                vectors.append([1.0, 0.9, 0.0])
            elif any(token in lowered for token in ("python", "sql", "fastapi", "mern", "langgraph")):
                vectors.append([0.95, 1.0, 0.0])
            elif any(token in lowered for token in ("ai", "machine learning", "llm", "forward deployed")):
                vectors.append([0.9, 0.0, 1.0])
            else:
                vectors.append([0.1, 0.1, 0.1])
        return np.asarray(vectors, dtype=np.float32)

    @staticmethod
    def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
        if left.size == 0 or right.size == 0:
            return 0.0
        return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right) + 1e-12))


class NLPPreprocessingTest(unittest.TestCase):
    def test_semantic_chunker_merges_related_voice_clauses(self) -> None:
        chunker = SemanticChunker(embedding_service=FakeEmbeddingService())

        chunks = chunker.chunk(
            "I am learning backend development, currently doing an AI internship, and I want to become a Forward Deployed Engineer."
        )

        self.assertEqual(len(chunks), 1)
        self.assertIn("backend development", chunks[0].text.casefold())
        self.assertIn("forward deployed engineer", chunks[0].text.casefold())

    def test_profile_extractor_identifies_skills_and_goal(self) -> None:
        extractor = ProfileExtractor(embedding_service=FakeEmbeddingService())

        result = extractor.extract(
            "I am learning backend development and I know Python, SQL, and FastAPI. I want to become a Forward Deployed Engineer."
        )

        self.assertIn("learning backend development", [item.casefold() for item in result.learning_intent])
        self.assertIn("Python", result.current_skills)
        self.assertIn("SQL", result.current_skills)
        self.assertIn("FastAPI", result.current_skills)
        self.assertIn("Forward Deployed Engineer", result.career_goals)

    def test_prepare_retrieval_context_returns_structured_payload(self) -> None:
        context = prepare_retrieval_context("I want to learn backend development and become a backend engineer.")

        payload = context.to_payload()
        self.assertEqual(set(payload), {"learning_intent", "current_skills", "career_goals", "semantic_chunks", "confidence_score"})
        self.assertGreaterEqual(payload["confidence_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
