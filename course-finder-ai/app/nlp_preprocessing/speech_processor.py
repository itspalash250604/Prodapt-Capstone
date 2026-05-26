"""Transcript cleanup for noisy voice input."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from app.nlp_preprocessing.models import TranscriptQuality


logger = logging.getLogger(__name__)

FILLER_RE = re.compile(r"\b(?:um+|uh+|erm+|ah+|like|you know|i mean)\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
SPACING_RE = re.compile(r"\s+([,.;:!?])")
PUNCTUATION_RE = re.compile(r"[,.!?;:]")
NOISE_TOKEN_RE = re.compile(r"[^\w\s,.!?;:'\-+/()]", re.UNICODE)


@dataclass(frozen=True)
class PreprocessedTranscript:
    """Cleaned transcript plus quality metrics."""

    original_text: str
    normalized_text: str
    quality: TranscriptQuality


def preprocess_transcript(text: str) -> PreprocessedTranscript:
    """Normalize speech-to-text output while preserving meaning."""

    if not text or not text.strip():
        raise ValueError("transcript must not be empty")

    original_text = text.strip()
    normalized = original_text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    normalized = FILLER_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    normalized = SPACING_RE.sub(r"\1", normalized)
    normalized = re.sub(r"([,.;:!?])(?!\s|$)", r"\1 ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()

    quality = estimate_quality(original_text, normalized)
    if quality.noise_score >= 0.65:
        logger.info("Transcript quality is low; enabling fallback handling")

    return PreprocessedTranscript(
        original_text=original_text,
        normalized_text=normalized,
        quality=quality,
    )


def estimate_quality(original_text: str, normalized_text: str) -> TranscriptQuality:
    """Score transcript cleanliness for downstream confidence scoring."""

    original_words = original_text.split()
    normalized_words = normalized_text.split()
    word_count = len(normalized_words)
    filler_count = len(FILLER_RE.findall(original_text))
    punctuation_count = len(PUNCTUATION_RE.findall(normalized_text))
    noisy_tokens = len(NOISE_TOKEN_RE.findall(original_text))

    filler_ratio = filler_count / max(1, len(original_words))
    punctuation_ratio = punctuation_count / max(1, word_count)
    noise_score = min(1.0, 0.55 * filler_ratio + 0.35 * (noisy_tokens / max(1, len(original_words))) + 0.1 * (1.0 if word_count < 4 else 0.0))

    return TranscriptQuality(
        word_count=word_count,
        filler_ratio=filler_ratio,
        punctuation_ratio=punctuation_ratio,
        noise_score=noise_score,
    )
