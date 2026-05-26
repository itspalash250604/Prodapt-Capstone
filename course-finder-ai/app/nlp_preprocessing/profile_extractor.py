"""Profile extraction from cleaned transcripts."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from app.nlp_preprocessing.embedding_service import EmbeddingService, get_embedding_service


logger = logging.getLogger(__name__)

LEARNING_MARKERS = (
    "i am learning",
    "i'm learning",
    "im learning",
    "i want to learn",
    "i'm trying to learn",
    "im trying to learn",
    "i'm improving",
    "i am improving",
    "i want to improve",
    "upskilling in",
    "learning about",
    "studying",
    "building toward",
)

SKILL_MARKERS = (
    "my skills include",
    "skills include",
    "i know",
    "i have experience with",
    "i work with",
    "currently using",
    "i'm using",
    "im using",
    "i use",
    "currently doing",
    "currently working on",
    "my stack includes",
)

GOAL_MARKERS = (
    "i want to become",
    "i want to be",
    "i want a career as",
    "i want a career in",
    "my goal is",
    "career goal is",
    "i aim to become",
    "i'm aiming to become",
    "im aiming to become",
    "i'm aiming for",
    "im aiming for",
    "looking to become",
    "transition into",
    "switch into",
)

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python", "py"),
    "FastAPI": ("fastapi", "fast api"),
    "MERN": ("mern", "mongo express react node"),
    "LangGraph": ("langgraph",),
    "SQL": ("sql", "structured query language", "postgres", "postgresql"),
    "Backend Development": ("backend development", "backend", "server-side", "api development"),
    "AI Systems": ("ai systems", "artificial intelligence", "ai", "llm", "llms"),
    "Machine Learning": ("machine learning", "ml"),
    "Data Analysis": ("data analysis", "analytics", "excel", "power bi", "tableau"),
    "React": ("react", "reactjs", "react.js"),
    "Node.js": ("node", "nodejs", "node.js"),
    "TypeScript": ("typescript", "ts"),
    "JavaScript": ("javascript", "js"),
    "AWS": ("aws", "amazon web services"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "PostgreSQL": ("postgresql", "postgres"),
    "Prompt Engineering": ("prompt engineering",),
}

CAREER_GOAL_LABELS = (
    "AI Engineer",
    "Backend Engineer",
    "Forward Deployed Engineer",
    "Machine Learning Engineer",
    "Data Engineer",
    "Data Analyst",
    "Full Stack Engineer",
    "Software Engineer",
    "DevOps Engineer",
    "Product Engineer",
)

GOAL_ALIASES: dict[str, tuple[str, ...]] = {
    "Forward Deployed Engineer": ("forward deployed engineer", "fde"),
    "AI Engineer": ("ai engineer", "artificial intelligence engineer"),
    "Backend Engineer": ("backend engineer", "backend developer"),
    "Machine Learning Engineer": ("machine learning engineer", "ml engineer"),
    "Data Engineer": ("data engineer",),
    "Data Analyst": ("data analyst",),
    "Full Stack Engineer": ("full stack engineer", "full-stack engineer"),
    "Software Engineer": ("software engineer",),
    "DevOps Engineer": ("devops engineer",),
    "Product Engineer": ("product engineer",),
}


@dataclass(frozen=True)
class ProfileExtraction:
    """Structured profile extraction results."""

    learning_intent: list[str]
    current_skills: list[str]
    career_goals: list[str]
    confidence_score: float


class ProfileExtractor:
    """Extracts learning intent, current skills, and career goals."""

    def __init__(self, embedding_service: EmbeddingService | None = None) -> None:
        self.embedding_service = embedding_service or get_embedding_service()

    def extract(self, transcript: str, chunks: list[str] | None = None) -> ProfileExtraction:
        normalized = transcript.strip()
        if not normalized:
            return ProfileExtraction([], [], [], 0.0)

        learning_intent = self._extract_learning_intent(normalized)
        current_skills = self._extract_current_skills(normalized)
        career_goals = self._extract_career_goals(normalized)

        if chunks:
            for chunk in chunks:
                if not learning_intent:
                    learning_intent.extend(self._extract_learning_intent(chunk))
                if not current_skills:
                    current_skills.extend(self._extract_current_skills(chunk))
                if not career_goals:
                    career_goals.extend(self._extract_career_goals(chunk))

        learning_intent = self._dedupe_preserve_order(learning_intent)
        current_skills = self._dedupe_preserve_order(self._canonicalize_skills(current_skills, normalized))
        career_goals = self._dedupe_preserve_order(self._canonicalize_goals(career_goals, normalized))

        confidence = self._compute_confidence(normalized, learning_intent, current_skills, career_goals)
        return ProfileExtraction(learning_intent, current_skills, career_goals, confidence)

    def _extract_learning_intent(self, transcript: str) -> list[str]:
        lowered = transcript.casefold()
        results: list[str] = []

        for marker in LEARNING_MARKERS:
            start = lowered.find(marker)
            if start == -1:
                continue
            tail = transcript[start + len(marker) :]
            phrase = self._capture_clause(tail)
            phrase = self._clean_phrase(phrase)
            if phrase:
                prefix = "improving" if "improv" in marker else "learning" if "learn" in marker or "stud" in marker else "transitioning into"
                results.append(f"{prefix} {phrase}".strip())

        if not results:
            for phrase in self._find_alias_matches(transcript, SKILL_ALIASES):
                results.append(f"learning {phrase.casefold()}".strip())

        return results

    def _extract_current_skills(self, transcript: str) -> list[str]:
        lowered = transcript.casefold()
        results: list[str] = []

        for marker in SKILL_MARKERS:
            start = lowered.find(marker)
            if start == -1:
                continue
            tail = transcript[start + len(marker) :]
            phrase = self._capture_clause(tail)
            for candidate in self._split_list_phrase(phrase):
                cleaned = self._clean_phrase(candidate)
                if cleaned:
                    results.append(cleaned)

        results.extend(self._find_alias_matches(transcript, SKILL_ALIASES))
        return results

    def _extract_career_goals(self, transcript: str) -> list[str]:
        lowered = transcript.casefold()
        results: list[str] = []

        for marker in GOAL_MARKERS:
            start = lowered.find(marker)
            if start == -1:
                continue
            tail = transcript[start + len(marker) :]
            phrase = self._capture_clause(tail)
            cleaned = self._clean_phrase(phrase)
            if cleaned:
                results.append(cleaned)

        results.extend(self._find_alias_matches(transcript, GOAL_ALIASES))
        return results

    @staticmethod
    def _capture_clause(text: str) -> str:
        # Split on sentence terminators or common continuation phrases that
        # introduce another clause the speaker uses to enumerate skills or goals.
        pattern = (
            r"(?:\.|\?|!|;|"
            r"\band\s+i\s+want\b|\band\s+i\s+am\b|\band\s+i\s+know\b|\band\s+i\s+have\b|"
            r"\bbut\b|\bbecause\b|\bso\b)"
        )
        clause = re.split(pattern, text, maxsplit=1, flags=re.IGNORECASE)[0]
        return clause.strip(" ,.;:-")

    @staticmethod
    def _split_list_phrase(text: str) -> list[str]:
        if not text:
            return []
        pieces = re.split(r",|/|\band\b|\bor\b", text, flags=re.IGNORECASE)
        return [piece.strip() for piece in pieces if piece.strip()]

    @staticmethod
    def _clean_phrase(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip(" ,.;:-")
        cleaned = re.sub(r"^(?:in|with|about|on|into|for|to)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _find_alias_matches(self, transcript: str, alias_map: dict[str, tuple[str, ...]]) -> list[str]:
        lowered = transcript.casefold()
        matches: list[str] = []
        for label, aliases in alias_map.items():
            for alias in aliases:
                if alias in lowered:
                    matches.append(label)
                    break
        return matches

    def _canonicalize_skills(self, candidates: list[str], transcript: str) -> list[str]:
        canonical = list(SKILL_ALIASES)
        return self._canonicalize_candidates(candidates, transcript, canonical, SKILL_ALIASES)

    def _canonicalize_goals(self, candidates: list[str], transcript: str) -> list[str]:
        return self._canonicalize_candidates(candidates, transcript, list(CAREER_GOAL_LABELS), GOAL_ALIASES)

    def _canonicalize_candidates(
        self,
        candidates: list[str],
        transcript: str,
        labels: list[str],
        alias_map: dict[str, tuple[str, ...]],
    ) -> list[str]:
        if not candidates:
            return []

        resolved: list[str] = []
        for candidate in candidates:
            lower_candidate = candidate.casefold()
            exact_label = self._exact_alias_match(lower_candidate, alias_map)
            if exact_label:
                resolved.append(exact_label)
                continue

            if self.embedding_service is None:
                resolved.append(candidate.title())
                continue

            best_label = self._best_embedding_match(candidate, labels)
            if best_label is not None:
                resolved.append(best_label)
            else:
                resolved.append(candidate.title())

        return resolved

    @staticmethod
    def _exact_alias_match(text: str, alias_map: dict[str, tuple[str, ...]]) -> str | None:
        for label, aliases in alias_map.items():
            if any(alias in text for alias in aliases):
                return label
        return None

    def _best_embedding_match(self, candidate: str, labels: list[str]) -> str | None:
        try:
            vectors = self.embedding_service.embed_texts([candidate, *labels])
        except Exception:
            return None

        if vectors.shape[0] < 2:
            return None

        candidate_vector = vectors[0]
        label_vectors = vectors[1:]
        similarities = [self.embedding_service.cosine_similarity(candidate_vector, label_vector) for label_vector in label_vectors]
        if not similarities:
            return None

        best_index = int(max(range(len(similarities)), key=lambda index: similarities[index]))
        if similarities[best_index] < 0.42:
            return None
        return labels[best_index]

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            key = item.casefold().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(item)
        return ordered

    @staticmethod
    def _compute_confidence(
        transcript: str,
        learning_intent: list[str],
        current_skills: list[str],
        career_goals: list[str],
    ) -> float:
        word_count = len(transcript.split())
        if word_count == 0:
            return 0.0

        extraction_signal = min(1.0, 0.25 * len(learning_intent) + 0.35 * len(current_skills) + 0.4 * len(career_goals))
        transcript_signal = min(1.0, word_count / 18.0)
        confidence = 0.45 * extraction_signal + 0.35 * transcript_signal + 0.2
        return round(min(1.0, confidence), 3)
