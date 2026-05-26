"""Model identifiers used across the recommendation pipeline."""

from __future__ import annotations

import os


QWEN_MODEL_NAME = os.getenv("COURSE_FINDER_QWEN_MODEL", "Qwen/Qwen3.6-12B")
DEEPSEEK_MODEL_NAME = os.getenv("COURSE_FINDER_DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B")
