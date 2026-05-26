"""Helpers for converting PDF and audio uploads into plain text."""

from __future__ import annotations

import io
import os
from functools import lru_cache

import fitz
import numpy as np
import soundfile as sf
from fastapi import HTTPException, UploadFile, status
import logging
from app.nlp_preprocessing import prepare_retrieval_context
from faster_whisper import WhisperModel

WHISPER_MODEL_NAME = os.getenv("COURSE_FINDER_WHISPER_MODEL", "tiny")
WHISPER_DEVICE = os.getenv("COURSE_FINDER_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("COURSE_FINDER_WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = os.getenv("COURSE_FINDER_WHISPER_LANGUAGE", "en")


logger = logging.getLogger(__name__)


def extract_pdf_text(file: UploadFile) -> dict[str, object]:
    """Extract searchable text from a PDF using PyMuPDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported for PDF intake.")

    payload = file.file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded PDF is empty.")

    try:
        document = fitz.open(stream=payload, filetype="pdf")
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to read PDF content: {exc}") from exc

    page_texts: list[str] = []
    for page in document:
        page_text = page.get_text("text").strip()
        if page_text:
            page_texts.append(page_text)

    text = "\n\n".join(page_texts).strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text could be extracted from the PDF.")

    return {
        "source_type": "pdf",
        "filename": file.filename,
        "text": text,
        "page_count": len(document),
    }


def transcribe_audio(file: UploadFile) -> dict[str, object]:
    """Transcribe uploaded audio with a Whisper model from Hugging Face."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file is required.")

    payload = file.file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio file is empty.")

    try:
        asr = load_whisper_model()
        waveform, sample_rate = decode_audio_payload(payload)
        if sample_rate != 16000:
            waveform = resample_audio(waveform, sample_rate, 16000)
        segments, info = asr.transcribe(
            waveform,
            language=WHISPER_LANGUAGE or None,
            beam_size=1,
            vad_filter=True,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to transcribe audio: {exc}") from exc

    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No transcript could be generated from the audio.")
    # Use the preprocessing layer to produce structured context
    retrieval_context = prepare_retrieval_context(transcript)
    logger.info(
        "Prepared voice retrieval context with confidence %.3f and %d semantic chunks",
        retrieval_context.confidence_score,
        len(retrieval_context.semantic_chunks),
    )

    career_goal = retrieval_context.career_goals[0] if retrieval_context.career_goals else None

    return {
        "source_type": "audio",
        "filename": file.filename,
        "text": retrieval_context.normalized_text,
        "current_skills": retrieval_context.current_skills,
        "career_goal": career_goal,
        "learning_intent": retrieval_context.learning_intent,
        "career_goals": retrieval_context.career_goals,
        "semantic_chunks": retrieval_context.semantic_chunks,
        "confidence_score": retrieval_context.confidence_score,
        "duration_seconds": None,
        "model_name": WHISPER_MODEL_NAME,
        "language": getattr(info, "language", WHISPER_LANGUAGE),
        "transcription_engine": "faster-whisper",
    }


def decode_audio_payload(payload: bytes) -> tuple[np.ndarray, int]:
    """Decode an uploaded audio payload into a mono float32 waveform."""
    try:
        waveform, sample_rate = sf.read(io.BytesIO(payload), dtype="float32", always_2d=False)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to decode audio payload: {exc}") from exc

    if waveform.size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio file is empty after decoding.")

    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)

    return np.asarray(waveform, dtype=np.float32), int(sample_rate)


@lru_cache(maxsize=1)
def load_whisper_model() -> WhisperModel:
    """Load the faster-whisper speech-to-text model lazily."""
    return WhisperModel(
        WHISPER_MODEL_NAME,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
    )


def resample_audio(waveform: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
    """Resample a mono waveform to the requested sample rate."""
    if original_rate == target_rate:
        return waveform

    duration = waveform.shape[0] / float(original_rate)
    target_length = max(1, int(duration * target_rate))
    source_positions = np.linspace(0.0, duration, num=waveform.shape[0], endpoint=False)
    target_positions = np.linspace(0.0, duration, num=target_length, endpoint=False)
    return np.interp(target_positions, source_positions, waveform).astype(np.float32)


def extract_voice_profile(transcript: str) -> dict[str, object]:
    """Backward-compatible structured profile extraction for voice input."""

    retrieval_context = prepare_retrieval_context(transcript)
    return {
        "current_skills": retrieval_context.current_skills,
        "career_goal": retrieval_context.career_goals[0] if retrieval_context.career_goals else None,
        "learning_intent": retrieval_context.learning_intent,
        "career_goals": retrieval_context.career_goals,
        "semantic_chunks": retrieval_context.semantic_chunks,
        "confidence_score": retrieval_context.confidence_score,
    }


def heuristic_voice_profile(transcript: str) -> dict[str, object]:
    """Fallback profile extraction when the LLM is unavailable."""
    lowered = transcript.casefold()
    current_skills: list[str] = []

    for marker in ("i know", "i have", "my skills are", "skills include"):
        if marker in lowered:
            segment = lowered.split(marker, 1)[1]
            segment = segment.split(" and i want", 1)[0]
            segment = segment.split(" and i am", 1)[0]
            segment = segment.split(". ", 1)[0]
            candidates = [item.strip(" ,.") for item in segment.replace(" and ", ",").split(",")]
            current_skills = [skill.title() for skill in candidates if skill]
            break

    career_goal = None
    goal_markers = ["i want to become", "i want to be", "my goal is", "career goal is", "i want a career in"]
    for marker in goal_markers:
        if marker in lowered:
            segment = lowered.split(marker, 1)[1].strip()
            segment = segment.split(".", 1)[0].strip()
            career_goal = segment.title() if segment else None
            break

    return {
        "current_skills": current_skills,
        "career_goal": career_goal,
    }
