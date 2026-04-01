"""
services/idea_collision_service.py

LLM-driven idea collision service.

Purpose:
- Pull Topological Void context from vector store
- Ask one LLM to generate multiple invention candidates
- Return structured candidates for downstream TID formatting
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import OpenAI

from configs.settings import settings
from vectordb.store import CollectionName, DeepThoughtVectorStore


@dataclass
class IdeaCandidate:
    title: str
    one_liner: str
    novelty_thesis: str
    feasibility_thesis: str
    market_thesis: str
    why_now: str
    innovation: int
    implementation_difficulty: int
    commercial_value: int
    technical_risk: int
    prior_art_conflict_risk: int
    problem_statement: str
    prior_art_gap: str
    proposed_invention: str
    architecture_overview: str
    implementation_plan: str
    validation_plan: str
    draft_claims: List[str]
    risks_and_mitigations: List[str]
    references: List[str]


class IdeaCollisionService:
    """Generate idea candidates from void context using one LLM."""

    def __init__(
        self,
        store: Optional[DeepThoughtVectorStore] = None,
        model: Optional[str] = None,
        temperature: float = 0.8,
    ):
        self.store = store or DeepThoughtVectorStore()
        self.model = model or settings.maverick_model
        self.temperature = temperature
        self.client = OpenAI(
            base_url=settings.internal_llm_base_url,
            api_key=settings.internal_llm_api_key,
        )

    def generate(
        self,
        domain: str,
        target: str,
        existing_solutions: Optional[List[str]] = None,
        collection_names: Optional[List[str]] = None,
        domain_filter: Optional[str] = None,
        lambda_val: float = 0.7,
        top_k_voids: int = 5,
        n_ideas: int = 3,
    ) -> List[IdeaCandidate]:
        """Find voids and generate idea candidates."""

        collections = None
        if collection_names:
            collections = [CollectionName(c) for c in collection_names]

        landscape = self.store.find_topological_voids(
            target_description=target,
            existing_solutions=existing_solutions,
            collections=collections,
            domain_filter=domain_filter,
            lambda_val=lambda_val,
            top_k=top_k_voids,
        )

        void_context = landscape.to_maverick_context()
        payload = self._generate_with_llm(
            domain=domain,
            target=target,
            void_context=void_context,
            n_ideas=n_ideas,
        )

        raw_candidates = payload.get("candidates", [])
        candidates: List[IdeaCandidate] = []

        for item in raw_candidates:
            try:
                candidates.append(self._to_candidate(item))
            except Exception as exc:
                logger.warning(f"Skip malformed candidate: {exc}")

        return candidates

    def _generate_with_llm(
        self,
        domain: str,
        target: str,
        void_context: str,
        n_ideas: int,
    ) -> Dict[str, Any]:
        system_prompt = (
            "You are an invention strategist. "
            "Generate high-novelty but technically plausible technical invention ideas. "
            "Output JSON only, no markdown, no extra text."
        )

        user_prompt = f"""
Domain: {domain}
Target: {target}
Requested ideas: {n_ideas}

Void context from retrieval:
{void_context}

Return STRICT JSON with this schema:
{{
  "candidates": [
    {{
      "title": "string",
      "one_liner": "string",
      "novelty_thesis": "string",
      "feasibility_thesis": "string",
      "market_thesis": "string",
      "why_now": "string",
      "scores": {{
        "innovation": 1-5,
        "implementation_difficulty": 1-5,
        "commercial_value": 1-5,
        "technical_risk": 1-5,
        "prior_art_conflict_risk": 1-5
      }},
      "tid_detail": {{
        "problem_statement": "string",
        "prior_art_gap": "string",
        "proposed_invention": "string",
        "architecture_overview": "string",
        "implementation_plan": "string",
        "validation_plan": "string",
        "draft_claims": ["string", "string"],
        "risks_and_mitigations": ["string", "string"],
        "references": ["string", "string"]
      }}
    }}
  ]
}}

Rules:
- Scores must be integers 1..5.
- Ideas must be mutually distinct.
- Tie every idea to the provided void context.
""".strip()

        logger.info(
            f"LLM idea collision | model={self.model} | n_ideas={n_ideas}"
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = (resp.choices[0].message.content or "").strip()
        data = self._parse_json(content)
        if not isinstance(data, dict) or "candidates" not in data:
            raise ValueError("LLM output does not match expected JSON schema")
        return data

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON content and recover from fenced code blocks."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
        if fence_match:
            return json.loads(fence_match.group(1))

        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            return json.loads(brace_match.group(1))

        raise ValueError("Unable to parse JSON from LLM response")

    def _to_candidate(self, item: Dict[str, Any]) -> IdeaCandidate:
        scores = item.get("scores", {})
        detail = item.get("tid_detail", {})

        return IdeaCandidate(
            title=str(item.get("title", "Untitled Idea")),
            one_liner=str(item.get("one_liner", "")),
            novelty_thesis=str(item.get("novelty_thesis", "")),
            feasibility_thesis=str(item.get("feasibility_thesis", "")),
            market_thesis=str(item.get("market_thesis", "")),
            why_now=str(item.get("why_now", "")),
            innovation=int(scores.get("innovation", 3)),
            implementation_difficulty=int(scores.get("implementation_difficulty", 3)),
            commercial_value=int(scores.get("commercial_value", 3)),
            technical_risk=int(scores.get("technical_risk", 3)),
            prior_art_conflict_risk=int(scores.get("prior_art_conflict_risk", 3)),
            problem_statement=str(detail.get("problem_statement", "")),
            prior_art_gap=str(detail.get("prior_art_gap", "")),
            proposed_invention=str(detail.get("proposed_invention", "")),
            architecture_overview=str(detail.get("architecture_overview", "")),
            implementation_plan=str(detail.get("implementation_plan", "")),
            validation_plan=str(detail.get("validation_plan", "")),
            draft_claims=[str(x) for x in detail.get("draft_claims", [])],
            risks_and_mitigations=[str(x) for x in detail.get("risks_and_mitigations", [])],
            references=[str(x) for x in detail.get("references", [])],
        )
