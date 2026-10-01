import pytest
from unittest.mock import AsyncMock, patch

from app.rag.hybrid_retriever import (
    deduplicate_hybrid_sources,
    execute_hybrid_retrieval,
    normalize_source_item,
    rerank_results,
)
from app.rag.retrieval_planner import RetrievalMode, plan_retrieval_strategy
from app.rag.answer_generator import generate_legal_answer


def test_retrieval_planner_live_verify_trigger():
    mode = plan_retrieval_strategy("What is the latest amendment regarding consumer rights?")
    assert mode == RetrievalMode.LIVE_VERIFY


def test_retrieval_planner_hybrid_mode():
    mode = plan_retrieval_strategy("What are my consumer rights?", category="consumer_rights")
    assert mode == RetrievalMode.HYBRID


def test_deduplicate_hybrid_sources():
    local = [{
        "chunk_id": "c1",
        "title": "Consumer Protection Act, 2019",
        "provision_number": "35",
        "official_url": "https://indiacode.gov.in/handle/1234",
        "source_mode": "local"
    }]
    live = [{
        "chunk_id": "live_1",
        "title": "Consumer Protection Act, 2019",
        "provision_number": "35",
        "official_url": "https://indiacode.gov.in/handle/1234",
        "source_mode": "live"
    }]
    deduped = deduplicate_hybrid_sources(local, live)
    assert len(deduped) == 1
    assert deduped[0]["source_mode"] == "live"  # Live version prioritized


@pytest.mark.anyio
async def test_live_unavailable_local_sufficient_answers_safely():
    mock_local = [{
        "chunk_id": "c1",
        "source_id": "s1",
        "title": "Consumer Protection Act, 2019",
        "authority": "District Forum",
        "category": "consumer_rights",
        "provision_type": "section",
        "provision_number": "35",
        "text": "A consumer may file a complaint before the District Commission in relation to goods or services. [SOURCE_1]",
        "score": 0.88,
    }]

    with patch("app.rag.hybrid_retriever.search_legal_chunks", return_value=mock_local):
        with patch("app.rag.hybrid_retriever.search_india_code", return_value=[]):
            with patch("app.rag.answer_generator.generate_text", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = "A consumer may file a complaint before the District Commission. [SOURCE_1]\n\nThis information is for general legal awareness and does not replace advice from a qualified legal professional."

                ans = await generate_legal_answer("How to file a consumer complaint?")
                assert ans["answer"] is not None
                assert len(ans["sources"]) > 0
                assert ans["sources"][0]["provision_number"] == "35"


@pytest.mark.anyio
async def test_live_unavailable_local_insufficient_fails_closed():
    with patch("app.rag.hybrid_retriever.search_legal_chunks", return_value=[]):
        with patch("app.rag.hybrid_retriever.search_india_code", return_value=[]):
            ans = await generate_legal_answer("Nonexistent law query")
            assert "could not find sufficiently relevant" in ans["answer"].lower()
            assert ans["sources"] == []
