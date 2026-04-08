"""
services/target_mutation_service.py

Random Walk & Mutate service:
1) Sample a random chunk from VectorDB.
2) Ask LLM to mutate it into a new retrieval target.
"""

from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List, Optional

from configs.settings import settings
from agents.llm_client import LLMClient
from vectordb.store import CollectionName, DeepThoughtVectorStore


# Diverse mutation hints — picked randomly each call so targets rotate across
# the actual corpus domains (include/, arch/x86/, tools/, mm/, kernel/).
# No technology is hardcoded; the seed chunk drives the domain.
_MUTATION_HINTS = [
    "Identify the single most specific unsolved performance bottleneck in this code path "
    "and propose a hardware-software co-design solution using x86 CPU microarchitecture features.",

    "Find a locking, synchronization, or memory-ordering invariant in this code that could be "
    "strengthened or eliminated using x86 hardware primitives (TSX, CLWB, MFENCE, monitor/mwait).",

    "Propose a novel interaction between this subsystem's hot path and x86 hardware telemetry "
    "(PEBS, LBR, PMU, MSR) that reduces latency or improves scheduling decisions.",

    "Identify a scalability bottleneck in this subsystem for high-core-count x86 Xeon systems "
    "and propose a kernel-level architectural fix that avoids global locks.",

    "Find an unexplored cross-subsystem interaction between this code and the Linux memory "
    "subsystem (TLB, page tables, NUMA, CXL) that creates a patentable optimization opportunity.",

    "Identify where this code path interacts with x86 cache hierarchy (L1/L2/L3, LLC, prefetcher) "
    "in a sub-optimal way and propose a concrete kernel fix.",

    "Propose a novel use of x86 virtualization extensions (VT-x, VMCS, EPT, APIC virtualization) "
    "to accelerate or harden this kernel subsystem.",

    "Find a specific data structure or algorithm in this code that could be redesigned to exploit "
    "x86 SIMD (AVX-512, AMX) or accelerator offload for kernel-mode computation.",

    "Identify an interrupt handling, IPI, or wakeup latency problem in this code path and propose "
    "a solution using x86 APIC, Posted Interrupts, or MSI-X innovations.",

    "Find a cross-subsystem power and performance trade-off in this code (RAPL, C-states, P-states) "
    "that could be resolved with a new kernel policy backed by hardware feedback.",
]

DEFAULT_MUTATION_HINT = _MUTATION_HINTS[0]


def _random_mutation_hint() -> str:
    """Return a randomly chosen mutation hint from the corpus-aligned pool."""
    return random.choice(_MUTATION_HINTS)


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
        mutation_hint: str = "",
    ) -> Dict[str, Any]:
        # If no hint specified (or explicitly empty), pick one randomly
        # so targets rotate across corpus domains rather than locking onto BPF.
        if not mutation_hint:
            mutation_hint = _random_mutation_hint()
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
2. Stay in the same kernel subsystem as the seed chunk — do not switch to an unrelated subsystem.
3. Pure userspace or ARM/RISC-V concepts are forbidden.
4. Must represent high-value patentable system-level innovation.
5. Output only a single English phrase with at most 15 words.
6. No markdown, no quotes, no explanation.
7. Do NOT force eBPF or BPF into the target unless the seed chunk is from net/bpf or kernel/bpf.

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
