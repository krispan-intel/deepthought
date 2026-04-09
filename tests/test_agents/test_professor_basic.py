"""
Basic smoke tests for Professor Agent.
(Full test suite deferred to tester agent)
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.professor import ProfessorAgent
from agents.state import DraftIdea, PipelineState


def test_professor_skip_when_no_drafts():
    """Professor should skip when state has no drafts."""
    professor = ProfessorAgent()
    state = PipelineState(domain="test", target="test")
    state.drafts = []

    result = professor.run(state)

    assert result.metadata["professor_review"]["verdict"] == "SKIP"
    assert "No drafts to review" in result.metadata["professor_review"]["reason"]


def test_professor_skip_when_disabled():
    """Professor should skip when professor_enabled=False."""
    from configs.settings import settings

    original = settings.professor_enabled
    try:
        settings.professor_enabled = False

        professor = ProfessorAgent()
        state = PipelineState(domain="test", target="test")
        state.drafts = [MagicMock(spec=DraftIdea)]

        result = professor.run(state)

        assert result.metadata["professor_review"]["verdict"] == "SKIP"
        assert "disabled" in result.metadata["professor_review"]["reason"]

    finally:
        settings.professor_enabled = original


def test_professor_fallback_pass_on_parse_error():
    """Professor should fail-open (pass all) if LLM output is unparseable."""
    professor = ProfessorAgent()
    state = PipelineState(domain="test", target="test")
    state.topological_void_context = "dummy context"

    draft = MagicMock(spec=DraftIdea)
    draft.title = "Test Draft"
    draft.novelty_thesis = "Novel approach"
    draft.architecture_overview = "Architecture description"
    draft.implementation_plan = "Implementation steps"
    draft.draft_claims = ["Claim 1"]
    state.drafts = [draft]

    # Mock LLM to return unparseable output
    professor.llm = MagicMock()
    professor.llm.chat = MagicMock(return_value="This is not valid JSON at all")

    result = professor.run(state)

    # Should pass all drafts on parse error (fail-open)
    assert len(result.drafts) == 1
    assert result.metadata["professor_review"]["verdict"] == "PARSE_ERROR_PASS_ALL"
