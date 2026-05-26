"""Frontend configuration."""

from __future__ import annotations

import os


API_BASE_URL = os.getenv("COURSE_FINDER_API_URL", "http://127.0.0.1:8000")
RECOMMENDATIONS_ENDPOINT = f"{API_BASE_URL}/api/v1/recommendations"
HEALTH_ENDPOINT = f"{API_BASE_URL}/api/v1/health"
REQUEST_TIMEOUT_SECONDS = 120

DIFFICULTY_OPTIONS = ["Any", "Beginner", "Mixed", "Intermediate", "Advanced"]
COURSE_TYPE_OPTIONS = [
    "Any",
    "Course",
    "Specialization",
    "Professional Certificate",
    "Guided Project",
    "Project",
]
