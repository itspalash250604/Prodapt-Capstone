"""File intake routes for PDF and audio normalization."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.api.v1.schemas import IntakeResponse
from app.intake.service import extract_pdf_text, transcribe_audio


router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/pdf", response_model=IntakeResponse)
def intake_pdf(file: UploadFile = File(...)) -> IntakeResponse:
    payload = extract_pdf_text(file)
    return IntakeResponse(**payload)


@router.post("/audio", response_model=IntakeResponse)
def intake_audio(file: UploadFile = File(...)) -> IntakeResponse:
    payload = transcribe_audio(file)
    return IntakeResponse(**payload)
