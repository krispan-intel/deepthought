"""
Tests for pipeline backpressure and queue depth controls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.pipeline import DeepThoughtPipeline
from agents.state import PipelineState
from configs.settings import settings


def test_maverick_queue_backpressure_applied():
    """Test that n_drafts is capped to max_maverick_queue_depth in parallel mode."""
    pipeline = DeepThoughtPipeline()
    state = PipelineState(domain="test", target="test target")
    state.topological_void_context = "dummy void context"
    state.void_statuses = [MagicMock()]

    original_parallel_mode = settings.pipeline_parallel_mode
    original_max_depth = settings.max_maverick_queue_depth

    try:
        settings.pipeline_parallel_mode = True
        settings.max_maverick_queue_depth = 5

        # Mock _run_maverick_parallel to capture the effective n_drafts
        captured_n_drafts = None

        def mock_parallel(s, n_drafts):
            nonlocal captured_n_drafts
            captured_n_drafts = n_drafts
            s.drafts = [MagicMock() for _ in range(n_drafts)]
            return s

        with patch.object(pipeline, "_run_maverick_parallel", side_effect=mock_parallel):
            with patch.object(pipeline.patent_shield, "run", return_value=state):
                with patch.object(pipeline.reality_checker, "run", return_value=state):
                    with patch.object(pipeline.debate_panel, "run", return_value=state):
                        # Request 10 drafts, should be capped to 5
                        pipeline.run(state, n_drafts=10, top_k_voids=5)

        assert captured_n_drafts == 5, f"Expected n_drafts=5, got {captured_n_drafts}"

    finally:
        settings.pipeline_parallel_mode = original_parallel_mode
        settings.max_maverick_queue_depth = original_max_depth


def test_maverick_queue_no_cap_when_within_limit():
    """Test that n_drafts is not capped when below max_maverick_queue_depth."""
    pipeline = DeepThoughtPipeline()
    state = PipelineState(domain="test", target="test target")
    state.topological_void_context = "dummy void context"
    state.void_statuses = [MagicMock()]

    original_parallel_mode = settings.pipeline_parallel_mode
    original_max_depth = settings.max_maverick_queue_depth

    try:
        settings.pipeline_parallel_mode = True
        settings.max_maverick_queue_depth = 10

        captured_n_drafts = None

        def mock_parallel(s, n_drafts):
            nonlocal captured_n_drafts
            captured_n_drafts = n_drafts
            s.drafts = [MagicMock() for _ in range(n_drafts)]
            return s

        with patch.object(pipeline, "_run_maverick_parallel", side_effect=mock_parallel):
            with patch.object(pipeline.patent_shield, "run", return_value=state):
                with patch.object(pipeline.reality_checker, "run", return_value=state):
                    with patch.object(pipeline.debate_panel, "run", return_value=state):
                        # Request 3 drafts, should not be capped
                        pipeline.run(state, n_drafts=3, top_k_voids=5)

        assert captured_n_drafts == 3, f"Expected n_drafts=3, got {captured_n_drafts}"

    finally:
        settings.pipeline_parallel_mode = original_parallel_mode
        settings.max_maverick_queue_depth = original_max_depth


def test_debate_panel_respects_queue_depth():
    """Test that debate panel enforces max_debate_queue_depth."""
    from agents.debate_panel import DebatePanelAgent

    agent = DebatePanelAgent()
    state = PipelineState(domain="test", target="test")
    state.drafts = [MagicMock(title="Test Draft")]

    original_max_depth = settings.max_debate_queue_depth

    try:
        # Set max_debate_queue_depth lower than the 4 specialists
        settings.max_debate_queue_depth = 2

        # Should raise RuntimeError due to specialist count exceeding limit
        with pytest.raises(RuntimeError, match="exceeds max_debate_queue_depth"):
            agent.run(state)

    finally:
        settings.max_debate_queue_depth = original_max_depth
