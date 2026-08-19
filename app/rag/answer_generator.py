from typing import Any

from app.rag.citation_guard import (
    extract_citations,
    validate_citations,
)
from app.rag.confidence import (
    evaluate_retrieval_confidence,
)
from app.rag.context_builder import (
    build_rag_context,
)
from app.rag.llm_client import (
    generate_text,
)
from app.rag.prompt import (
    CITATION_RETRY_INSTRUCTIONS,
    LEGAL_SYSTEM_INSTRUCTIONS,
    build_retry_prompt,
    build_user_prompt,
)
from app.rag.retriever import (
    search_legal_chunks,
)
from app.rag.source_formatter import (
    format_sources_for_response,
)


INSUFFICIENT_CONTEXT_MESSAGE = (
    "I could not find sufficiently relevant authoritative "
    "material in the available legal knowledge base."
)

DISCLAIMER = (
    "This information is for general legal awareness and does "
    "not replace advice from a qualified legal professional."
)


def ensure_disclaimer(answer: str) -> str:
    if DISCLAIMER.lower() in answer.lower():
        return answer

    return (
        f"{answer.rstrip()}\n\n"
        f"{DISCLAIMER}"
    )


def build_fallback_response(
    retrieved_count: int = 0,
    confidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    answer = (
        f"{INSUFFICIENT_CONTEXT_MESSAGE}\n\n"
        f"{DISCLAIMER}"
    )

    return {
        "answer": answer,
        "sources": [],
        "retrieved_count": retrieved_count,
        "citation_validation": {
            "valid": True,
            "found": [],
            "valid_citations": [],
            "invalid_citations": [],
        },
        "citation_retry_used": False,
        "confidence": confidence,
    }


async def generate_legal_answer(
    question: str,
    category: str | None = None,
    top_k: int = 5,
    retrieval_query: str | None = None,
) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty")

    # -----------------------------------------
    # 1. RETRIEVAL
    # -----------------------------------------
    effective_retrieval_query = (
        retrieval_query.strip()
        if retrieval_query
        else question
    )

    results = search_legal_chunks(
        query=effective_retrieval_query,
        top_k=top_k,
        category=category,
    )

    if not results:
        return build_fallback_response(retrieved_count=0)

    # -----------------------------------------
    # 2. RETRIEVAL CONFIDENCE GATE
    # -----------------------------------------
    confidence = evaluate_retrieval_confidence(results)

    if not confidence["accepted"]:
        return build_fallback_response(
            retrieved_count=len(results),
            confidence=confidence,
        )

    # -----------------------------------------
    # 3. BUILD CONTROLLED RAG CONTEXT
    # -----------------------------------------
    rag_context = build_rag_context(
        results,
        max_sources=top_k,
    )

    if rag_context["source_count"] == 0:
        return build_fallback_response(
            retrieved_count=len(results),
            confidence=confidence,
        )

    allowed_citations = rag_context["allowed_citations"]

    # -----------------------------------------
    # 4. FIRST LLM ATTEMPT
    # -----------------------------------------
    user_prompt = build_user_prompt(
        question=question,
        context=rag_context["context"],
        allowed_citations=allowed_citations,
    )

    answer = await generate_text(
        instructions=LEGAL_SYSTEM_INSTRUCTIONS,
        input_text=user_prompt,
    )

    validation = validate_citations(
        answer=answer,
        allowed_citations=allowed_citations,
    )

    used_citations = extract_citations(answer)
    retry_used = False

    # -----------------------------------------
    # 5. ONE CONTROLLED CITATION RETRY
    # -----------------------------------------
    if not validation["valid"] or not used_citations:
        retry_used = True

        retry_prompt = build_retry_prompt(
            question=question,
            context=rag_context["context"],
            allowed_citations=allowed_citations,
            previous_answer=answer,
        )

        answer = await generate_text(
            instructions=(
                LEGAL_SYSTEM_INSTRUCTIONS
                + "\n\n"
                + CITATION_RETRY_INSTRUCTIONS
            ),
            input_text=retry_prompt,
        )

        validation = validate_citations(
            answer=answer,
            allowed_citations=allowed_citations,
        )

        used_citations = extract_citations(answer)

    # -----------------------------------------
    # 6. FAIL CLOSED IF CITATIONS STILL INVALID
    # -----------------------------------------
    if not validation["valid"] or not used_citations:
        fallback = build_fallback_response(
            retrieved_count=len(results),
            confidence=confidence,
        )
        fallback["citation_retry_used"] = retry_used
        return fallback

    # -----------------------------------------
    # 7. BUILD USER-VISIBLE SOURCE METADATA
    # -----------------------------------------
    sources = format_sources_for_response(
        citation_map=rag_context["citation_map"],
        used_citations=used_citations,
    )

    answer = ensure_disclaimer(answer)

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(results),
        "citation_validation": validation,
        "citation_retry_used": retry_used,
        "confidence": confidence,
    }
