"""FastAPI API tests."""

from __future__ import annotations

import io
import wave
from unittest.mock import patch

import unittest

import fitz
from fastapi.testclient import TestClient

from app.main import create_app


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health_check(self) -> None:
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_recommendation_request_validation_rejects_short_query(self) -> None:
        response = self.client.post(
            "/api/v1/recommendations",
            json={
                "query": "ai",
                "current_skills": [],
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_recommendation_request_validation_rejects_top_k_above_candidate_k(self) -> None:
        response = self.client.post(
            "/api/v1/recommendations",
            json={
                "query": "machine learning engineer",
                "current_skills": ["Python"],
                "candidate_k": 2,
                "top_k": 3,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("top_k", response.text)

    def test_pdf_intake_extracts_text(self) -> None:
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "Build better course recommendations")
        pdf_bytes = document.tobytes()

        response = self.client.post(
            "/api/v1/intake/pdf",
            files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_type"], "pdf")
        self.assertIn("Build better course recommendations", response.json()["text"])

    def test_audio_intake_uses_transcription_layer(self) -> None:
        audio_bytes = _build_silent_wav()
        test_case = self

        class FakeModel:
            def transcribe(self, audio_input, **kwargs):
                test_case.assertEqual(kwargs.get("beam_size"), 1)
                test_case.assertIsNotNone(audio_input)
                return ([type("Segment", (), {"text": "I want to become a data analyst."})()], type("Info", (), {"language": "en"})())

        with patch("app.intake.service.load_whisper_model", return_value=FakeModel()) as model_mock, patch(
            "app.intake.service.prepare_retrieval_context",
        ) as context_mock:
            context_mock.return_value.normalized_text = "I want to become a data analyst."
            context_mock.return_value.current_skills = ["Python", "SQL"]
            context_mock.return_value.career_goals = ["Data Analyst"]
            context_mock.return_value.learning_intent = ["learning data analysis"]
            context_mock.return_value.semantic_chunks = ["I want to become a data analyst."]
            context_mock.return_value.confidence_score = 0.92

            response = self.client.post(
                "/api/v1/intake/audio",
                files={"file": ("sample.wav", audio_bytes, "audio/wav")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_type"], "audio")
        self.assertEqual(response.json()["text"], "I want to become a data analyst.")
        self.assertEqual(response.json()["transcription_engine"], "faster-whisper")
        self.assertEqual(response.json()["current_skills"], ["Python", "SQL"])
        self.assertEqual(response.json()["career_goal"], "Data Analyst")
        model_mock.assert_called_once()
        context_mock.assert_called_once()


def _build_silent_wav() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 1600)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
