"""
agents/llm_client.py

Minimal LLM helper for OpenAI-compatible and Anthropic calls.
"""

from __future__ import annotations

import re
import time
from typing import List

from loguru import logger
from openai import OpenAI

from configs.settings import settings


class LLMClient:
    def __init__(self):
        self.timeout_seconds = settings.llm_request_timeout_seconds
        self.max_attempts = max(1, settings.llm_request_max_attempts)
        self.backoff_seconds = max(0.0, settings.llm_request_backoff_seconds)
        self._anthropic_enabled = bool(settings.anthropic_api_key)
        self._openai = OpenAI(
            base_url=settings.internal_llm_base_url,
            api_key=settings.internal_llm_api_key,
            timeout=self.timeout_seconds,
            max_retries=0,
        )

    def chat(self, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        model_candidates = self._build_model_candidates(model)
        final_error: RuntimeError | None = None

        for model_index, selected_model in enumerate(model_candidates, start=1):
            last_error: RuntimeError | None = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    resp = self._openai.chat.completions.create(
                        model=selected_model,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    if model_index > 1:
                        logger.warning(f"LLM fallback succeeded with model={selected_model}")
                    return (resp.choices[0].message.content or "").strip()
                except Exception as exc:
                    message = self._format_exception(exc)
                    is_transient = self._is_transient_error(message)
                    is_model_unavailable = self._is_model_unavailable_error(message)
                    last_error = RuntimeError(f"model={selected_model}: {message}")

                    if attempt < self.max_attempts and is_transient and not is_model_unavailable:
                        delay = self.backoff_seconds * attempt
                        logger.warning(
                            f"LLM request failed (model={selected_model}, attempt {attempt}/{self.max_attempts}), "
                            f"retrying in {delay:.1f}s: {message}"
                        )
                        time.sleep(delay)
                        continue

                    break

            final_error = last_error
            has_next_model = model_index < len(model_candidates)
            if has_next_model:
                logger.warning(
                    f"LLM model failed, trying fallback model ({model_index + 1}/{len(model_candidates)}): "
                    f"{last_error}"
                )

        raise final_error or RuntimeError("LLM request failed")

    def chat_reality_checker(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        # Prefer Anthropic for reality checker if key exists, else fall back.
        if self._anthropic_enabled and settings.anthropic_api_key:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                resp = client.messages.create(
                    model=settings.reality_checker_model,
                    max_tokens=2200,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text_parts = []
                for block in resp.content:
                    value = getattr(block, "text", None)
                    if value:
                        text_parts.append(value)
                return "\n".join(text_parts).strip()
            except Exception as exc:
                if self._is_anthropic_forbidden_error(str(exc)):
                    self._anthropic_enabled = False
                logger.warning(f"Anthropic call failed, fallback to internal model: {exc}")

        return self.chat(
            model=settings.reality_checker_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        text = str(exc).strip()
        lowered = text.lower()
        if "<!doctype html" not in lowered and "<html" not in lowered:
            return text

        title = LLMClient._extract_html_fragment(text, "title")
        heading = LLMClient._extract_html_fragment(text, "h1")
        url_match = re.search(
            r"<td>\s*URL\s*</td>\s*<td>\s*(.*?)\s*</td>",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        parts = []
        if title:
            parts.append(title)
        if heading and heading != title:
            parts.append(heading)
        if url_match:
            parts.append(f"url={LLMClient._compact_whitespace(url_match.group(1))}")

        if parts:
            return " | ".join(parts)

        stripped = re.sub(r"<[^>]+>", " ", text)
        return LLMClient._compact_whitespace(stripped)

    @staticmethod
    def _extract_html_fragment(text: str, tag: str) -> str:
        match = re.search(
            rf"<{tag}[^>]*>\s*(.*?)\s*</{tag}>",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return ""
        return LLMClient._compact_whitespace(re.sub(r"<[^>]+>", " ", match.group(1)))

    @staticmethod
    def _compact_whitespace(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def _is_transient_error(message: str) -> bool:
        lowered = message.lower()
        markers = (
            "502",
            "503",
            "504",
            "gateway timeout",
            "bad gateway",
            "service unavailable",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "connection reset",
            "remote server did not respond",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _is_model_unavailable_error(message: str) -> bool:
        lowered = message.lower()
        markers = (
            "no fallback model group found",
            "received model group",
            "model_group",
            "model not found",
            "unknown model",
            "unsupported model",
        )
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _parse_fallback_models() -> List[str]:
        raw = settings.llm_fallback_models or ""
        return [item.strip() for item in raw.split(",") if item.strip()]

    def _build_model_candidates(self, primary_model: str) -> List[str]:
        candidates: List[str] = []
        for model_name in [primary_model, *self._parse_fallback_models()]:
            if model_name and model_name not in candidates:
                candidates.append(model_name)
        return candidates

    @staticmethod
    def _is_anthropic_forbidden_error(message: str) -> bool:
        lowered = message.lower()
        markers = (
            "error code: 401",
            "error code: 403",
            "forbidden",
            "request not allowed",
            "permission",
            "unauthorized",
        )
        return any(marker in lowered for marker in markers)
