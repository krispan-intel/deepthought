"""
services/target_mutation_service.py

Random Walk & Mutate service:
1) Sample a random chunk from VectorDB.
2) Ask LLM to mutate it into a new retrieval target.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from configs.settings import settings
from agents.llm_client import LLMClient
from vectordb.store import CollectionName, DeepThoughtVectorStore


DEFAULT_MUTATION_HINT = "Combine this seed concept with BPF techniques and propose an aggressive cross-domain hypothesis."


class TargetMutationService:
    def __init__(
        self,
        llm: LLMClient | None = None,
        store: DeepThoughtVectorStore | None = None,
        model: str | None = None,
    ):
        self.llm = llm or LLMClient()
        self.store = store or DeepThoughtVectorStore()
        self.model = model or settings.maverick_model

    def mutate_target(
        self,
        base_target: str,
        collection_names: Optional[List[str]] = None,
        mutation_hint: str = DEFAULT_MUTATION_HINT,
    ) -> Dict[str, Any]:
        collections = self._parse_collections(collection_names)
        sampled = self.store.sample_random_document(collections=collections)
        if not sampled:
            return {
                "mutated_target": base_target,
                "seed_doc_id": "",
                "seed_label": "",
                "seed_collection": "",
                "seed_excerpt": "",
                "mutation_rationale": "vector store is empty",
                "used_random_walk": False,
            }

        seed_text = (sampled.document.content or "")[:1800]
        seed_label = sampled.to_tech_vector().label
        seed_collection = sampled.collection.value

        system_prompt = (
            "You are a visionary Principal Engineer at Intel specializing in x86 architecture "
            "and Linux kernel HW/SW co-design."
        )

        user_prompt = f"""
Base mission:
{base_target}

Mutation instruction:
{mutation_hint}

Random seed chunk metadata:
- collection: {seed_collection}
- label: {seed_label}
- doc_id: {sampled.document.doc_id}

Random seed chunk excerpt:
{seed_text}

Task:
Mutate the core technical concept of the random seed into one highly specific,
unsolved optimization target.

Critical constraints:
1. Must tightly couple x86 hardware architecture with Linux kernel internals.
2. Pure userspace or ARM/RISC-V concepts are forbidden.
3. Must represent high-value patentable system-level innovation.
4. Output only a single English phrase with at most 15 words.
5. No markdown, no quotes, no explanation.

Output now:
""".strip()

        raw = self.llm.chat(
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.0,
        )
        mutated_target = self._extract_phrase(raw) or base_target

        return {
            "mutated_target": mutated_target,
            "seed_doc_id": sampled.document.doc_id,
            "seed_label": seed_label,
            "seed_collection": seed_collection,
            "seed_excerpt": seed_text,
            "mutation_rationale": "mutated from random seed chunk",
            "used_random_walk": True,
        }

    @staticmethod
    def _parse_collections(collection_names: Optional[List[str]]) -> Optional[List[CollectionName]]:
        if not collection_names:
            return None

        parsed: List[CollectionName] = []
        for item in collection_names:
            text = str(item).strip()
            if not text:
                continue
            try:
                parsed.append(CollectionName(text))
            except ValueError:
                continue
        return parsed or None

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
        if fenced:
            return json.loads(fenced.group(1))

        braces = re.search(r"(\{[\s\S]*\})", text)
        if braces:
            return json.loads(braces.group(1))

        return {}

    @staticmethod
    def _extract_phrase(text: str) -> str:
        # Best effort: take first non-empty line and enforce <= 15 words.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""

        phrase = lines[0].strip().strip('"').strip("'")
        phrase = re.sub(r"[`*_#]", "", phrase)
        words = phrase.split()
        if len(words) > 15:
            phrase = " ".join(words[:15])
        return phrase
