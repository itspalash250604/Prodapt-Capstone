"""Shared data structures for transcript preprocessing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranscriptQuality:
    """Lightweight quality signals for a transcript."""

    word_count: int
    filler_ratio: float
    punctuation_ratio: float
    noise_score: float


@dataclass(frozen=True)
class RetrievalContext:
    """Structured output produced from a spoken transcript."""

    learning_intent: list[str] = field(default_factory=list)
    current_skills: list[str] = field(default_factory=list)
    career_goals: list[str] = field(default_factory=list)
    semantic_chunks: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    normalized_text: str = ""
    quality: TranscriptQuality | None = None

    def to_payload(self) -> dict[str, object]:
        """Return the public payload expected by the intake API."""

        return {
            "learning_intent": self.learning_intent,
            "current_skills": self.current_skills,
            "career_goals": self.career_goals,
            "semantic_chunks": self.semantic_chunks,
            "confidence_score": self.confidence_score,
        }
