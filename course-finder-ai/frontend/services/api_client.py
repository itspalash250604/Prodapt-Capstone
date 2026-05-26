"""FastAPI client used by the Streamlit frontend."""

from __future__ import annotations

from typing import Any

import requests

from frontend.config import HEALTH_ENDPOINT, RECOMMENDATIONS_ENDPOINT, REQUEST_TIMEOUT_SECONDS


class ApiClientError(RuntimeError):
    """Raised when the frontend cannot retrieve API data."""


def check_health() -> dict[str, Any]:
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiClientError(f"Backend health check failed: {exc}") from exc


def get_recommendations(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(
            RECOMMENDATIONS_ENDPOINT,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        detail = safe_error_detail(exc.response)
        raise ApiClientError(f"Recommendation request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"Could not connect to recommendation API: {exc}") from exc


def safe_error_detail(response: requests.Response | None) -> str:
    if response is None:
        return "No response returned."
    try:
        return str(response.json())
    except ValueError:
        return response.text or f"HTTP {response.status_code}"
