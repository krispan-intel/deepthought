"""
agents/patent_shield.py

Patent Shield agent:
- Runs global prior-art fast screening.
- Uses Semantic Scholar API when enabled.
- Falls back to deterministic lexical overlap scoring.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen

from configs.settings import settings
from agents.state import PatentCheckResult, PipelineState


class PatentShieldAgent:
	def run(self, state: PipelineState) -> PipelineState:
		reports: List[PatentCheckResult] = []

		for idx, draft in enumerate(state.drafts):
			hits = self._collect_prior_art_hits(draft.title)
			overlap_score = self._lexical_overlap_score(
				draft_text=f"{draft.title} {draft.one_liner} {draft.proposed_invention}",
				existing_texts=state.existing_solutions,
			)
			hit_bonus = min(0.35, 0.12 * len(hits))
			conflict_score = max(0.0, min(1.0, overlap_score + hit_bonus))
			status = "FLAG" if conflict_score >= settings.patent_conflict_threshold else "PASS"
			rationale = (
				"High prior-art proximity detected"
				if status == "FLAG"
				else "No strong prior-art collision in fast screening"
			)

			if status == "FLAG":
				draft.prior_art_gap = (
					draft.prior_art_gap.strip() +
					"\n\nPatent Shield warning: potential prior-art overlap detected; tighten novelty boundary."
				).strip()

			reports.append(
				PatentCheckResult(
					draft_index=idx,
					status=status,
					conflict_score=round(conflict_score, 3),
					rationale=rationale,
					prior_art_hits=hits,
				)
			)

		state.patent_checks = reports
		state.metadata["patent_shield_reports"] = [asdict(r) for r in reports]

		if reports and all(r.status == "FLAG" for r in reports):
			state.run_status = "REJECTED"
			state.last_error = "Patent Shield rejected all drafts due to prior-art conflict risk"
			state.metadata["rejected_reason"] = state.last_error

		return state

	def _collect_prior_art_hits(self, query: str) -> List[str]:
		if not settings.patent_api_enabled:
			return []

		params = {
			"query": query,
			"limit": settings.patent_shield_max_results,
			"fields": "title,year,url,citationCount",
		}
		url = f"{settings.semantic_scholar_api_url}?{urlencode(params)}"

		try:
			with urlopen(url, timeout=settings.patent_shield_timeout_seconds) as response:
				payload = json.loads(response.read().decode("utf-8"))
		except Exception:
			return []

		data = payload.get("data", []) if isinstance(payload, dict) else []
		hits: List[str] = []
		for item in data:
			title = str(item.get("title", "")).strip()
			if title:
				hits.append(title)
		return hits

	@staticmethod
	def _lexical_overlap_score(draft_text: str, existing_texts: List[str]) -> float:
		draft_tokens = PatentShieldAgent._tokenize(draft_text)
		if not draft_tokens or not existing_texts:
			return 0.0

		best = 0.0
		for text in existing_texts:
			base = PatentShieldAgent._tokenize(text)
			if not base:
				continue
			intersection = draft_tokens.intersection(base)
			union = draft_tokens.union(base)
			if not union:
				continue
			best = max(best, len(intersection) / len(union))
		return best

	@staticmethod
	def _tokenize(text: str) -> set[str]:
		cleaned = [tok.strip().lower() for tok in (text or "").replace("/", " ").replace("-", " ").split()]
		return {tok for tok in cleaned if len(tok) >= 4}
