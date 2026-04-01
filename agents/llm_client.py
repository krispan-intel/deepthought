"""
agents/llm_client.py

Minimal LLM helper for OpenAI-compatible and Anthropic calls.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from openai import OpenAI

from configs.settings import settings


class LLMClient:
    def __init__(self):
        self._openai = OpenAI(
            base_url=settings.internal_llm_base_url,
            api_key=settings.internal_llm_api_key,
        )

    def chat(self, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        resp = self._openai.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    def chat_reality_checker(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        # Prefer Anthropic for reality checker if key exists, else fall back.
        if settings.anthropic_api_key:
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
                logger.warning(f"Anthropic call failed, fallback to internal model: {exc}")

        return self.chat(
            model=settings.reality_checker_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )
