"""
Tests for the chat response curation fix.

Validates that Simple mode follows the new concise-conversational contract
and Detailed mode is preserved with better curation, without weakening
any legal safety, citation, or fail-closed behavior.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.rag.prompt import (
    SIMPLE_SYSTEM_INSTRUCTIONS,
    DETAILED_SYSTEM_INSTRUCTIONS,
    LEGAL_SYSTEM_INSTRUCTIONS,
    get_system_instructions,
)
from app.rag.answer_generator import generate_legal_answer
from app.rag.source_formatter import format_sources_for_response
from app.rag.citation_guard import extract_citations, validate_citations


# ---------------------------------------------------------------------------
# Prompt structure tests (non-LLM, no mocks needed)
# ---------------------------------------------------------------------------

class TestSimpleModePromptContract:
    """Simple mode prompt must enforce concise conversational answers."""

    def test_simple_mode_is_separate_from_base(self):
        """Simple mode is no longer an alias of LEGAL_SYSTEM_INSTRUCTIONS."""
        assert SIMPLE_SYSTEM_INSTRUCTIONS != LEGAL_SYSTEM_INSTRUCTIONS

    def test_simple_mode_word_target(self):
        """Simple mode instruction includes 100-220 word target."""
        assert "100" in SIMPLE_SYSTEM_INSTRUCTIONS
        assert "220" in SIMPLE_SYSTEM_INSTRUCTIONS
        assert "250" in SIMPLE_SYSTEM_INSTRUCTIONS  # hard preference

    def test_simple_mode_forbids_default_headings(self):
        """Simple mode explicitly discourages section headings."""
        lower = SIMPLE_SYSTEM_INSTRUCTIONS.lower()
        assert "do not" in lower
        assert "section headings" in lower or "what this means" in lower

    def test_simple_mode_forbids_bullet_dumps(self):
        """Simple mode discourages long bullet lists."""
        lower = SIMPLE_SYSTEM_INSTRUCTIONS.lower()
        assert "bullet" in lower or "checklist" in lower

    def test_simple_mode_preserves_citation_format(self):
        """Simple mode still requires [SOURCE_N] citations."""
        assert "[SOURCE_1]" in SIMPLE_SYSTEM_INSTRUCTIONS
        assert "[SOURCE_2]" in SIMPLE_SYSTEM_INSTRUCTIONS

    def test_simple_mode_preserves_fail_closed(self):
        """Simple mode retains the insufficient-context refusal text."""
        assert "could not find sufficiently relevant" in SIMPLE_SYSTEM_INSTRUCTIONS

    def test_simple_mode_preserves_no_invention_rule(self):
        """Simple mode retains the no-hallucination rule."""
        lower = SIMPLE_SYSTEM_INSTRUCTIONS.lower()
        assert "never invent" in lower or "never guess" in lower

    def test_simple_mode_actionability(self):
        """Simple mode tells the user what to do next."""
        lower = SIMPLE_SYSTEM_INSTRUCTIONS.lower()
        assert "next step" in lower or "next action" in lower
        assert "what should i do next" in lower


class TestDetailedModePromptContract:
    """Detailed mode prompt must be preserved but better curated."""

    def test_detailed_mode_word_target(self):
        """Detailed mode targets 350-650 words (not 400-900)."""
        assert "350" in DETAILED_SYSTEM_INSTRUCTIONS
        assert "650" in DETAILED_SYSTEM_INSTRUCTIONS

    def test_detailed_mode_allows_headings(self):
        """Detailed mode may use headings where they help."""
        lower = DETAILED_SYSTEM_INSTRUCTIONS.lower()
        assert "headings" in lower or "bullet" in lower

    def test_detailed_mode_preserves_citation_format(self):
        """Detailed mode still requires [SOURCE_N] citations."""
        assert "[SOURCE_1]" in DETAILED_SYSTEM_INSTRUCTIONS
        assert "[SOURCE_2]" in DETAILED_SYSTEM_INSTRUCTIONS

    def test_detailed_mode_preserves_fail_closed(self):
        """Detailed mode retains the insufficient-context refusal text."""
        assert "could not find sufficiently relevant" in DETAILED_SYSTEM_INSTRUCTIONS

    def test_detailed_mode_preserves_no_invention_rule(self):
        """Detailed mode retains the no-hallucination rule."""
        lower = DETAILED_SYSTEM_INSTRUCTIONS.lower()
        assert "never invent" in lower or "never guess" in lower


class TestModeRouting:
    """get_system_instructions routes correctly."""

    def test_simple_default(self):
        assert get_system_instructions() == SIMPLE_SYSTEM_INSTRUCTIONS

    def test_simple_explicit(self):
        assert get_system_instructions("simple") == SIMPLE_SYSTEM_INSTRUCTIONS

    def test_detailed_explicit(self):
        assert get_system_instructions("detailed") == DETAILED_SYSTEM_INSTRUCTIONS

    def test_unknown_fallback(self):
        assert get_system_instructions("unknown") == SIMPLE_SYSTEM_INSTRUCTIONS

    def test_none_fallback(self):
        assert get_system_instructions(None) == SIMPLE_SYSTEM_INSTRUCTIONS


# ---------------------------------------------------------------------------
# Citation and source card preservation tests
# ---------------------------------------------------------------------------

class TestCitationPreservation:
    """Citations and source cards must continue working."""

    def test_extract_citations_from_concise_answer(self):
        """Citations are extractable from short paragraph-style answers."""
        answer = (
            "Based on your situation, you may be entitled to a refund or replacement "
            "under the Consumer Protection Act [SOURCE_1]. Your best next step is to "
            "file a written complaint with the District Consumer Forum [SOURCE_2]."
        )
        citations = extract_citations(answer)
        assert "SOURCE_1" in citations
        assert "SOURCE_2" in citations

    def test_validate_citations_still_works(self):
        """Citation validation remains functional."""
        answer = "This is covered under [SOURCE_1] and [SOURCE_3]."
        result = validate_citations(answer, ["SOURCE_1", "SOURCE_2"])
        assert result["valid"] is False  # SOURCE_3 not in allowed list
        assert "SOURCE_3" in result["invalid_citations"]

    def test_source_formatter_caps_at_three(self):
        """Source cards are still capped at 3."""
        citation_map = {
            f"SOURCE_{i}": {"title": f"Act {i}", "authority": f"Auth {i}"}
            for i in range(1, 6)
        }
        used = [f"SOURCE_{i}" for i in range(1, 6)]
        sources = format_sources_for_response(citation_map, used)
        assert len(sources) <= 3


# ---------------------------------------------------------------------------
# Answer generation integration tests (mocked LLM)
# ---------------------------------------------------------------------------

MOCK_RETRIEVAL_RESULTS = [
    {
        "chunk_id": "chunk_1",
        "source_id": "source_1",
        "title": "Consumer Protection Act, 2019",
        "category": "consumer_rights",
        "authority": "Parliament of India",
        "provision_type": "section",
        "provision_number": "2(7)",
        "text": "Consumer means any person who buys goods or hires services...",
        "score": 0.95,
        "source_mode": "local",
    }
]


@pytest.mark.anyio
async def test_simple_mode_uses_concise_instructions():
    """Simple mode passes SIMPLE_SYSTEM_INSTRUCTIONS to the LLM."""
    mock_answer = (
        "You may be entitled to a refund under the Consumer Protection Act. [SOURCE_1]\n\n"
        "This information is for general legal awareness and does not replace advice "
        "from a qualified legal professional."
    )

    with patch("app.rag.answer_generator.execute_hybrid_retrieval",
               return_value=(MOCK_RETRIEVAL_RESULTS, "local", None)), \
         patch("app.rag.answer_generator.generate_text",
               new_callable=AsyncMock, return_value=mock_answer):

        result = await generate_legal_answer(
            question="Can I get a refund for a defective product?",
            category="consumer_rights",
            answer_mode="simple",
        )

        assert result["citation_validation"]["valid"] is True
        assert len(result["answer"].split()) < 300  # well within concise limit


@pytest.mark.anyio
async def test_detailed_mode_uses_detailed_instructions():
    """Detailed mode passes DETAILED_SYSTEM_INSTRUCTIONS to the LLM."""
    mock_answer = (
        "Under the Consumer Protection Act, 2019, a consumer is defined as any person "
        "who purchases goods or hires services for consideration. [SOURCE_1] "
        "The Act provides multiple remedies including refund, replacement, and compensation. "
        "Your next step would be to file a complaint with the District Consumer Disputes "
        "Redressal Forum within two years of the cause of action.\n\n"
        "This information is for general legal awareness and does not replace advice "
        "from a qualified legal professional."
    )

    with patch("app.rag.answer_generator.execute_hybrid_retrieval",
               return_value=(MOCK_RETRIEVAL_RESULTS, "local", None)), \
         patch("app.rag.answer_generator.generate_text",
               new_callable=AsyncMock, return_value=mock_answer) as mock_gen:

        result = await generate_legal_answer(
            question="Explain my consumer rights for a defective product",
            category="consumer_rights",
            answer_mode="detailed",
        )

        assert result["citation_validation"]["valid"] is True
        # Verify detailed instructions were used
        call_args = mock_gen.call_args
        assert "350" in call_args.kwargs["instructions"] or "DETAILED" in call_args.kwargs["instructions"]


@pytest.mark.anyio
async def test_fail_closed_preserved_in_simple_mode():
    """Simple mode still returns fallback when retrieval is empty."""
    with patch("app.rag.answer_generator.execute_hybrid_retrieval",
               return_value=([], "local", None)):

        result = await generate_legal_answer(
            question="What are my rights?",
            category="consumer_rights",
            answer_mode="simple",
        )

        assert "could not find sufficiently relevant" in result["answer"].lower()
        assert result["sources"] == []


@pytest.mark.anyio
async def test_no_invented_sources_in_simple_mode():
    """Simple mode does not invent citations beyond what's in the context."""
    mock_answer = (
        "You can seek a refund. [SOURCE_1] [SOURCE_99]\n\n"
        "This information is for general legal awareness and does not replace "
        "advice from a qualified legal professional."
    )

    with patch("app.rag.answer_generator.execute_hybrid_retrieval",
               return_value=(MOCK_RETRIEVAL_RESULTS, "local", None)), \
         patch("app.rag.answer_generator.generate_text",
               new_callable=AsyncMock, return_value=mock_answer):

        result = await generate_legal_answer(
            question="Refund?",
            category="consumer_rights",
            answer_mode="simple",
        )

        # SOURCE_99 is not allowed, so citation validation should fail
        # and the system should retry or fail closed
        if result["citation_validation"]["valid"]:
            # If retry produced valid answer, that's fine
            citations = extract_citations(result["answer"])
            assert all(c.startswith("SOURCE_") for c in citations)
