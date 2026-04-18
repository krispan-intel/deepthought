"""
agents/llm_client.py

Minimal LLM helper for OpenAI-compatible and Anthropic calls.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from typing import List

from loguru import logger
from openai import OpenAI

from configs.settings import settings


class LLMClient:
    def __init__(self, backend_override: str = None):
        self.timeout_seconds = settings.llm_request_timeout_seconds
        self.copilot_timeout_seconds = max(self.timeout_seconds, settings.copilot_cli_timeout_seconds)
        self.max_attempts = max(1, settings.llm_request_max_attempts)
        self.backoff_seconds = max(0.0, settings.llm_request_backoff_seconds)
        self.backend = (backend_override or settings.llm_backend or "openai").strip().lower()
        self.copilot_cli_command = settings.copilot_cli_command or "gh copilot"
        self.copilot_prompt_max_chars = max(2000, settings.copilot_prompt_max_chars)
        self._anthropic_enabled = bool(settings.anthropic_api_key)
        self._openai = None
        if self.backend != "copilot_cli":
            self._openai = OpenAI(
                base_url=settings.internal_llm_base_url,
                api_key=settings.internal_llm_api_key,
                timeout=self.timeout_seconds,
                max_retries=0,
            )
        logger.info(
            "LLMClient initialized | backend={} | copilot_cli_command={} | timeout={}s | copilot_timeout={}s",
            self.backend,
            self.copilot_cli_command,
            self.timeout_seconds,
            self.copilot_timeout_seconds,
        )

    def chat(self, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        # claude_code_cli goes directly to `claude -p`, skip Anthropic API
        if self.backend == "claude_code_cli":
            return self._chat_with_claude_code_cli(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

        # Prefer Anthropic API for Claude models if key exists
        if model.startswith("claude-") and self._anthropic_enabled and settings.anthropic_api_key:
            try:
                import anthropic

                anthropic_base = getattr(settings, "anthropic_base_url", None) or None
                client = anthropic.Anthropic(
                    api_key=settings.anthropic_api_key,
                    base_url=anthropic_base,
                )
                resp = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text_parts = []
                for block in resp.content:
                    value = getattr(block, "text", None)
                    if value:
                        text_parts.append(value)
                logger.info(f"Anthropic API call succeeded | model={model}")
                return "\n".join(text_parts).strip()
            except Exception as exc:
                if self._is_anthropic_forbidden_error(str(exc)):
                    self._anthropic_enabled = False
                logger.warning(f"Anthropic call failed for {model}, fallback to {self.backend}: {exc}")
                # Fall through to backend below

        if self.backend == "copilot_cli":
            return self._chat_with_copilot_cli(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

        if self.backend == "claude_code_cli":
            return self._chat_with_claude_code_cli(
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

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
        if self.backend == "copilot_cli":
            return self.chat(
                model=settings.reality_checker_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )

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

    def _chat_with_copilot_cli(self, model: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        prompt = self._build_copilot_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if len(prompt) > self.copilot_prompt_max_chars:
            prompt = self._smart_truncate(prompt, self.copilot_prompt_max_chars)

        # Map pipeline model hints to available copilot models
        copilot_model = self._resolve_copilot_model(model)
        copilot_effort = settings.copilot_effort or "high"

        command = [
            *shlex.split(self.copilot_cli_command),
            "-p", prompt,
            "--model", copilot_model,
            "--effort", copilot_effort,
        ]
        logger.info(
            "LLM backend dispatch | backend=copilot_cli | model={} | effort={} | prompt_len={}",
            copilot_model,
            copilot_effort,
            len(prompt),
        )
        env = os.environ.copy()
        for name in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_PAT"):
            env.pop(name, None)

        last_error: RuntimeError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.copilot_timeout_seconds,
                    check=False,
                    env=env,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "Copilot CLI backend selected but command was not found. "
                    f"Set COPILOT_CLI_COMMAND or install `gh copilot`. Details: {exc}"
                ) from exc
            except subprocess.TimeoutExpired:
                last_error = RuntimeError(
                    f"copilot_cli timed out after {self.copilot_timeout_seconds} seconds"
                )
                if attempt < self.max_attempts:
                    delay = self.backoff_seconds * attempt
                    logger.warning(
                        "Copilot CLI timeout (attempt {}/{}) retrying in {:.1f}s",
                        attempt,
                        self.max_attempts,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error

            if result.returncode == 0:
                return self._strip_copilot_footer(result.stdout or "")

            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit_code={result.returncode}"
            last_error = RuntimeError(f"copilot_cli: {detail}")

            if attempt < self.max_attempts and self._is_transient_error(detail):
                delay = self.backoff_seconds * attempt
                logger.warning(
                    "Copilot CLI error (attempt {}/{}) retrying in {:.1f}s: {}",
                    attempt,
                    self.max_attempts,
                    delay,
                    detail,
                )
                time.sleep(delay)
                continue

            break

        raise last_error or RuntimeError("copilot_cli failed")

    @staticmethod
    def _build_copilot_prompt(system_prompt: str, user_prompt: str) -> str:
        # Extract JSON schema block from user_prompt and move to system_instructions
        # This ensures schema survives truncation (system_instructions is never cut)
        schema_block = ""
        cleaned_user = user_prompt.strip()

        # Detect common schema patterns: "Return strict JSON:", "OUTPUT FORMAT", "Return ONLY"
        schema_markers = [
            "Return strict JSON:",
            "Return ONLY strict JSON",
            "OUTPUT FORMAT (respond with ONLY this JSON",
            "OUTPUT FORMAT:",
            "Return ONLY this exact JSON",
        ]
        for marker in schema_markers:
            idx = cleaned_user.find(marker)
            if idx != -1:
                schema_block = cleaned_user[idx:]
                cleaned_user = cleaned_user[:idx].rstrip()
                break

        sys_parts = [
            "You MUST follow these instructions precisely. "
            "If structured output (JSON) is requested, return ONLY the JSON structure with no additional text.",
            "",
            system_prompt.strip(),
        ]
        if schema_block:
            sys_parts.extend(["", schema_block])

        return (
            "<system_instructions>\n"
            + "\n".join(sys_parts) + "\n"
            "</system_instructions>\n\n"
            "<user_request>\n"
            f"{cleaned_user}\n"
            "</user_request>"
        )

    @staticmethod
    def _smart_truncate(prompt: str, max_chars: int) -> str:
        """Truncate by cutting middle of <user_request>, preserving system_instructions and schema."""
        tag_start = prompt.find("<user_request>")
        tag_end = prompt.rfind("</user_request>")
        if tag_start == -1 or tag_end == -1:
            return prompt[:max_chars]

        head = prompt[:tag_start + len("<user_request>\n")]
        tail = prompt[tag_end:]  # "</user_request>"
        body = prompt[tag_start + len("<user_request>\n"):tag_end]

        available = max_chars - len(head) - len(tail) - 50  # 50 chars for truncation notice
        if available <= 0:
            return prompt[:max_chars]

        # Keep first 60% and last 40% of body (schema/instructions tend to be at the end)
        keep_front = int(available * 0.6)
        keep_back = available - keep_front
        truncated_body = body[:keep_front] + "\n\n[... content truncated ...]\n\n" + body[-keep_back:]

        return head + truncated_body + tail

    @staticmethod
    def _resolve_copilot_model(pipeline_model: str) -> str:
        """Map pipeline model names to available gh copilot model names."""
        m = (pipeline_model or "").lower().strip()
        # Opus-class → best available (gpt-5.4)
        if "opus" in m:
            return "gpt-5.4"
        # Sonnet-class → gpt-5.2
        if "sonnet" in m:
            return "gpt-5.2"
        # Haiku-class → gpt-5.4 mini (supports --effort, cheap/fast)
        if "haiku" in m:
            return "gpt-5.4"
        # DeepSeek / Qwen fallbacks → gpt-5.4
        if "deepseek" in m or "qwen" in m:
            return "gpt-5.4"
        # Default: use settings
        return settings.copilot_model or "gpt-5.4"

    def _chat_with_claude_code_cli(self, model: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Use 'claude -p' non-interactive mode as LLM backend."""
        prompt = self._build_copilot_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if len(prompt) > self.copilot_prompt_max_chars:
            prompt = self._smart_truncate(prompt, self.copilot_prompt_max_chars)

        claude_model = self._resolve_claude_code_model(model)
        effort = settings.copilot_effort or "high"

        command = [
            "claude",
            "-p", prompt,
            "--model", claude_model,
            "--effort", effort,
        ]
        logger.info(
            "LLM backend dispatch | backend=claude_code_cli | model={} | effort={} | prompt_len={}",
            claude_model,
            effort,
            len(prompt),
        )

        last_error: RuntimeError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.copilot_timeout_seconds,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "claude_code_cli backend selected but 'claude' command not found. "
                    f"Install Claude Code CLI. Details: {exc}"
                ) from exc
            except subprocess.TimeoutExpired:
                last_error = RuntimeError(
                    f"claude_code_cli timed out after {self.copilot_timeout_seconds}s"
                )
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
                    continue
                raise last_error

            if result.returncode == 0:
                return (result.stdout or "").strip()

            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit_code={result.returncode}"
            last_error = RuntimeError(f"claude_code_cli: {detail}")

            if attempt < self.max_attempts and self._is_transient_error(detail):
                time.sleep(self.backoff_seconds * attempt)
                continue
            break

        raise last_error or RuntimeError("claude_code_cli failed")

    @staticmethod
    def _resolve_claude_code_model(pipeline_model: str) -> str:
        """Map pipeline model names to claude CLI short aliases (opus/sonnet/haiku)."""
        m = (pipeline_model or "").lower().strip()
        # Opus-class
        if "opus" in m or "gpt-5.4" in m or "gpt-5.1" in m or "gpt-5.2" in m:
            return "opus"
        # Haiku-class (fast/cheap)
        if "haiku" in m or "nano" in m or "mini" in m:
            return "haiku"
        # Sonnet-class (default)
        return "sonnet"

    @staticmethod
    def _strip_copilot_footer(text: str) -> str:
        cleaned = re.sub(r"\nTotal usage est:[\s\S]*$", "", text.strip(), flags=re.MULTILINE)
        return cleaned.strip()

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
