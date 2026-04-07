from __future__ import annotations

import numpy as np

from core.deepthought_equation import DeepThoughtEquation, TechVector


def make_vector(name: str, values: list[float]) -> TechVector:
    return TechVector(id=name, label=name, vector=np.array(values, dtype=np.float32))


def test_calibrate_marginality_thresholds_returns_valid_band() -> None:
    engine = DeepThoughtEquation(lambda_val=0.7)
    target = make_vector("target", [1.0, 0.0, 0.0])
    candidates = [
        make_vector("a", [0.96, 0.22, 0.0]),
        make_vector("b", [0.88, 0.45, 0.0]),
        make_vector("c", [0.81, 0.58, 0.0]),
        make_vector("d", [0.71, 0.70, 0.0]),
    ]

    thresholds = engine.calibrate_marginality_thresholds(candidates, v_target=target)

    assert 0.18 <= thresholds.low < thresholds.high <= 0.82
    assert thresholds.sample_size > 0


def test_hybrid_void_selection_prefers_zero_cooccurrence_pairs() -> None:
    engine = DeepThoughtEquation(lambda_val=0.7)
    target = make_vector("target", [1.0, 0.0, 0.0])
    existing = [make_vector("existing", [0.5, 0.86, 0.0])]
    candidates = [
        make_vector("sched_feedback", [0.97, 0.20, 0.0]),
        make_vector("cache_pressure", [0.92, 0.38, 0.0]),
        make_vector("allocator", [0.65, 0.76, 0.0]),
    ]
    sparse_tokens = {
        "sched_feedback": ["scheduler", "latency", "feedback"],
        "cache_pressure": ["cache", "pressure", "rebalance"],
        "allocator": ["allocator", "memory", "pressure"],
    }

    def checker(left: list[str], right: list[str]) -> bool:
        blocked = {
            (tuple(sparse_tokens["cache_pressure"]), tuple(sparse_tokens["allocator"])),
            (tuple(sparse_tokens["allocator"]), tuple(sparse_tokens["cache_pressure"])),
        }
        return (tuple(left), tuple(right)) in blocked

    landscape = engine.find_hybrid_voids_iterative(
        v_target=target,
        candidates=candidates,
        existing=existing,
        sparse_tokens=sparse_tokens,
        global_cooccurrence_checker=checker,
        n_select=1,
        domain_threshold=0.4,
    )

    assert len(landscape.voids) == 1
    top = landscape.voids[0]
    assert top.sparse_overlap_count == 0
    assert "<>" in top.candidate.label
    assert "sched_feedback" in top.candidate.label


def test_hybrid_void_selection_returns_empty_when_no_valid_pairs() -> None:
    engine = DeepThoughtEquation(lambda_val=0.7)
    target = make_vector("target", [1.0, 0.0, 0.0])
    candidates = [
        make_vector("sched_feedback", [0.97, 0.20, 0.0]),
        make_vector("cache_pressure", [0.92, 0.38, 0.0]),
    ]
    sparse_tokens = {
        "sched_feedback": ["scheduler", "latency", "feedback"],
        "cache_pressure": ["cache", "pressure", "rebalance"],
    }

    landscape = engine.find_hybrid_voids_iterative(
        v_target=target,
        candidates=candidates,
        existing=[],
        sparse_tokens=sparse_tokens,
        global_cooccurrence_checker=lambda left, right: True,
        n_select=1,
        domain_threshold=0.4,
    )

    assert landscape.voids == []