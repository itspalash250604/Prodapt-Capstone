"""Lazy Hugging Face text generation helpers with deterministic fallbacks."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from app.llm.config import DEEPSEEK_MODEL_NAME, QWEN_MODEL_NAME


@lru_cache(maxsize=4)
def _load_generator(model_name: str):
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except Exception:
        return None

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype="auto",
        )
        model.eval()
        return tokenizer, model
    except Exception:
        return None


def generate_text(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
) -> str:
    generator = _load_generator(model_name)
    if generator is None:
        return ""

    tokenizer, model = generator
    prompt_text = build_prompt(tokenizer, system_prompt, user_prompt)

    try:
        import torch
    except Exception:
        return ""

    try:
        inputs = tokenizer(prompt_text, return_tensors="pt")
        input_ids = inputs["input_ids"].to(model.device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(model.device)

        generation_kwargs: dict[str, Any] = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "max_new_tokens": max_new_tokens,
            "pad_token_id": getattr(tokenizer, "eos_token_id", None),
            "eos_token_id": getattr(tokenizer, "eos_token_id", None),
        }
        if temperature > 0:
            generation_kwargs["do_sample"] = True
            generation_kwargs["temperature"] = temperature
            generation_kwargs["top_p"] = 0.9
        else:
            generation_kwargs["do_sample"] = False

        with torch.inference_mode():
            output_tokens = model.generate(**generation_kwargs)

        generated = output_tokens[0][input_ids.shape[-1] :]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()
    except Exception:
        return ""


def generate_json(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_text = generate_text(
        model_name,
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        temperature=0.0,
    )
    parsed = extract_json_object(raw_text)
    if parsed:
        return parsed
    return fallback_payload or {}


def qwen_generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
) -> str:
    return generate_text(
        QWEN_MODEL_NAME,
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
    )


def qwen_generate_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return generate_json(
        QWEN_MODEL_NAME,
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        fallback_payload=fallback_payload,
    )


def qwen_generate_structured(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return qwen_generate_json(
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        fallback_payload=fallback_payload,
    )


def deepseek_generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
) -> str:
    return generate_text(
        DEEPSEEK_MODEL_NAME,
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        temperature=0.0,
    )


def deepseek_generate_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return generate_json(
        DEEPSEEK_MODEL_NAME,
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        fallback_payload=fallback_payload,
    )


def deepseek_generate_structured(
    system_prompt: str,
    user_prompt: str,
    *,
    max_new_tokens: int = 256,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return deepseek_generate_json(
        system_prompt,
        user_prompt,
        max_new_tokens=max_new_tokens,
        fallback_payload=fallback_payload,
    )


def build_prompt(tokenizer: Any, system_prompt: str, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass

    return f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:\n"


def extract_json_object(text: str) -> dict[str, Any]:
    if not text:
        return {}

    candidates = [text]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed

    return {}
