"""Orchestration helpers for voice preprocessing."""

from __future__ import annotations

import logging

from app.nlp_preprocessing.models import RetrievalContext
from app.nlp_preprocessing.profile_extractor import ProfileExtractor
from app.nlp_preprocessing.semantic_chunker import SemanticChunker
from app.nlp_preprocessing.speech_processor import preprocess_transcript


logger = logging.getLogger(__name__)


def prepare_retrieval_context(transcript: str) -> RetrievalContext:
    """Clean, chunk, and extract structured profile hints from voice text."""

    processed = preprocess_transcript(transcript)
    chunker = SemanticChunker()
    chunks = chunker.chunk(processed.normalized_text)
    chunk_texts = [chunk.text for chunk in chunks]

    extractor = ProfileExtractor()
    profile = extractor.extract(processed.normalized_text, chunk_texts)

    confidence_score = _combine_confidence(processed, chunks, profile.confidence_score)
    context = RetrievalContext(
        learning_intent=profile.learning_intent,
        current_skills=profile.current_skills,
        career_goals=profile.career_goals,
        semantic_chunks=chunk_texts,
        confidence_score=confidence_score,
        normalized_text=processed.normalized_text,
        quality=processed.quality,
    )

    if confidence_score < 0.35:
        logger.info("Low-confidence voice context generated: %s", context)

    return context


def _combine_confidence(processed, chunks, extraction_confidence: float) -> float:
    if not processed.normalized_text.strip():
        return 0.0

    quality_score = max(0.0, 1.0 - processed.quality.noise_score)
    coherence_score = 1.0
    if chunks:
        coherence_score = sum(chunk.coherence for chunk in chunks) / len(chunks)

    score = 0.35 * quality_score + 0.35 * min(1.0, extraction_confidence) + 0.3 * coherence_score
    return round(max(0.0, min(1.0, score)), 3)
