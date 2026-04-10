"""
agents/json_parser.py

Bulletproof JSON parser with 3-pass repair strategy.
Handles common LLM output issues: control characters, trailing commas, extra data.

Pass 1: strict=False + raw_decode (handles control characters, extra data)
Pass 2: json-repair library (handles trailing commas, missing brackets, truncation)
Pass 3: LLM self-repair callback (optional, last resort)
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List

from loguru import logger


def robust_json_parse(
    text: str,
    *,
    llm_repair_callback: Callable[[str], str] | None = None,
    agent_name: str = "unknown",
) -> Dict[str, Any]:
    """
    Parse JSON from LLM output with 3-pass repair strategy.

    Args:
        text: Raw LLM output text
        llm_repair_callback: Optional callback for LLM self-repair (Pass 3)
        agent_name: Agent name for logging

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If all 3 passes fail to parse valid JSON
    """
    cleaned = _normalize_output(text)

    # Pass 1: standard parse across all candidate substrings
    # Uses strict=False + raw_decode to handle control characters and extra data
    decoder = json.JSONDecoder(strict=False)
    for candidate in _iter_json_candidates(cleaned):
        snippet = candidate.lstrip()
        if not snippet:
            continue
        try:
            # Try standard parse first
            parsed = json.loads(snippet, strict=False)
        except json.JSONDecodeError:
            try:
                # Try raw_decode for partial JSON with trailing data
                parsed, _ = decoder.raw_decode(snippet)
            except json.JSONDecodeError:
                continue
        payload = _coerce_payload(parsed)
        if payload is not None:
            return payload

    # Pass 2: json-repair handles trailing commas, missing brackets, truncated output
    try:
        from json_repair import repair_json

        repaired = repair_json(cleaned, return_objects=True)
        payload = _coerce_payload(repaired)
        if payload is not None:
            logger.warning(
                "{} JSON recovered via json-repair library (Pass 2)",
                agent_name,
            )
            return payload
    except ImportError:
        logger.debug(
            "{} json-repair library not available, skipping Pass 2",
            agent_name,
        )
    except Exception as exc:
        logger.debug(
            "{} json-repair failed | error={}",
            agent_name,
            exc,
        )

    # Pass 3: ask the LLM to fix its own output (one extra call, last resort)
    if llm_repair_callback is not None:
        try:
            fixed_raw = llm_repair_callback(cleaned[:6000])
            fixed_cleaned = _normalize_output(fixed_raw)
            for candidate in _iter_json_candidates(fixed_cleaned):
                snippet = candidate.lstrip()
                if not snippet:
                    continue
                try:
                    parsed = json.loads(snippet, strict=False)
                except json.JSONDecodeError:
                    continue
                payload = _coerce_payload(parsed)
                if payload is not None:
                    logger.warning(
                        "{} JSON recovered via LLM self-repair (Pass 3)",
                        agent_name,
                    )
                    return payload
        except Exception as repair_exc:
            logger.warning(
                "{} LLM self-repair (Pass 3) failed | error={}",
                agent_name,
                repair_exc,
            )

    raise ValueError(f"{agent_name} output is not valid JSON after 3-pass repair")


def _normalize_output(text: str) -> str:
    """Remove common ANSI escape sequences from terminal-rendered CLI output."""
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text or "").strip()


def _iter_json_candidates(text: str) -> List[str]:
    """
    Extract all possible JSON candidate substrings from text.

    Yields candidates in priority order:
    1. Original text
    2. Fenced code blocks (```json ... ```)
    3. Substrings starting with { or [
    """
    candidates: List[str] = [text]

    # Extract fenced code blocks
    for fenced in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE):
        candidates.append(fenced.group(1))

    # Extract substrings starting with { or [
    for token in ("{", "["):
        idx = text.find(token)
        while idx != -1:
            candidates.append(text[idx:])
            idx = text.find(token, idx + 1)

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for item in candidates:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def _coerce_payload(parsed: Any) -> Dict[str, Any] | None:
    """
    Coerce parsed JSON into expected dict format.

    Handles cases where LLM returns:
    - dict (expected)
    - list containing dict
    - list containing multiple dicts (pick first with expected keys)

    Returns:
        dict if coercion succeeds, None otherwise
    """
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        # Some LLMs wrap the response in an array
        for item in parsed:
            if isinstance(item, dict):
                # Prefer dicts that look like agent responses
                # (contain common keys like "drafts", "status", "verdict", etc.)
                if any(
                    key in item
                    for key in (
                        "drafts",
                        "status",
                        "verdict",
                        "final_verdict",
                        "verdicts",
                        "scorecard",
                    )
                ):
                    return item
        # Fallback: return first dict in list
        for item in parsed:
            if isinstance(item, dict):
                return item
    return None
