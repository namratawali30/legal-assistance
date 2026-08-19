from typing import Any

from app.rag.citation_guard import (
    extract_citations,
    validate_citations,
)
from app.rag.complaint_prompt import (
    CITATION_RETRY_INSTRUCTIONS,
    COMPLAINT_SYSTEM_INSTRUCTIONS,
    build_complaint_prompt,
    build_complaint_retry_prompt,
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
from app.rag.retriever import (
    search_legal_chunks,
)
from app.rag.source_formatter import (
    format_sources_for_response,
)


def build_complaint_retrieval_query(
    complaint: dict[str, Any],
) -> str:
    category = str(
        complaint.get(
            "category",
            "",
        )
    )

    facts = str(
        complaint.get(
            "facts",
            "",
        )
    ).strip()

    relief = str(
        complaint.get(
            "relief_requested",
            "",
        )
        or ""
    ).strip()

    incident_location = str(
        complaint.get(
            "incident_location",
            "",
        )
        or ""
    ).strip()

    # Avoid creating an excessively large embedding query.
    facts = facts[:4000]
    relief = relief[:1500]

    parts = [
        (
            "Find authoritative Indian legal provisions "
            "relevant to drafting this complaint."
        ),
        f"Legal category: {category}",
        f"Complaint facts: {facts}",
    ]

    if relief:
        parts.append(
            f"Requested relief: {relief}"
        )

    if incident_location:
        parts.append(
            f"Incident location: {incident_location}"
        )

    return "\n".join(parts)


async def generate_grounded_complaint(
    complaint: dict[str, Any],
    top_k: int = 5,
) -> dict[str, Any]:
    category = complaint.get(
        "category"
    )

    retrieval_query = (
        build_complaint_retrieval_query(
            complaint
        )
    )

    # ---------------------------------
    # 1. RETRIEVE LEGAL MATERIAL
    # ---------------------------------

    results = search_legal_chunks(
        query=retrieval_query,
        top_k=top_k,
        category=category,
    )

    if not results:
        return {
            "generated": False,
            "reason": "no_results",
            "generated_text": None,
            "sources": [],
            "confidence": None,
            "citation_retry_used": False,
        }

    # ---------------------------------
    # 2. CONFIDENCE GATE
    # ---------------------------------

    confidence = (
        evaluate_retrieval_confidence(
            results
        )
    )

    if not confidence[
        "accepted"
    ]:
        return {
            "generated": False,
            "reason": "low_relevance",
            "generated_text": None,
            "sources": [],
            "confidence": confidence,
            "citation_retry_used": False,
        }

    # ---------------------------------
    # 3. CONTROLLED LEGAL CONTEXT
    # ---------------------------------

    rag_context = build_rag_context(
        results,
        max_sources=top_k,
    )

    if (
        rag_context[
            "source_count"
        ]
        == 0
    ):
        return {
            "generated": False,
            "reason": "no_valid_context",
            "generated_text": None,
            "sources": [],
            "confidence": confidence,
            "citation_retry_used": False,
        }

    allowed_citations = (
        rag_context[
            "allowed_citations"
        ]
    )

    # ---------------------------------
    # 4. GENERATE FIRST DRAFT
    # ---------------------------------

    user_prompt = (
        build_complaint_prompt(
            complaint=complaint,
            context=rag_context[
                "context"
            ],
            allowed_citations=(
                allowed_citations
            ),
        )
    )

    answer = await generate_text(
        instructions=(
            COMPLAINT_SYSTEM_INSTRUCTIONS
        ),
        input_text=user_prompt,
    )

    validation = validate_citations(
        answer=answer,
        allowed_citations=(
            allowed_citations
        ),
    )

    used_citations = (
        extract_citations(
            answer
        )
    )

    retry_used = False

    # ---------------------------------
    # 5. ONE CITATION RETRY
    # ---------------------------------

    if (
        not validation["valid"]
        or not used_citations
    ):
        retry_used = True

        retry_prompt = (
            build_complaint_retry_prompt(
                complaint=complaint,
                context=rag_context[
                    "context"
                ],
                allowed_citations=(
                    allowed_citations
                ),
                previous_answer=answer,
            )
        )

        answer = await generate_text(
            instructions=(
                COMPLAINT_SYSTEM_INSTRUCTIONS
                + "\n\n"
                + CITATION_RETRY_INSTRUCTIONS
            ),
            input_text=retry_prompt,
        )

        validation = validate_citations(
            answer=answer,
            allowed_citations=(
                allowed_citations
            ),
        )

        used_citations = (
            extract_citations(
                answer
            )
        )

    # ---------------------------------
    # 6. FAIL CLOSED
    # ---------------------------------

    if (
        not validation["valid"]
        or not used_citations
    ):
        return {
            "generated": False,
            "reason": (
                "citation_validation_failed"
            ),
            "generated_text": None,
            "sources": [],
            "confidence": confidence,
            "citation_validation":
                validation,
            "citation_retry_used":
                retry_used,
        }

    # ---------------------------------
    # 7. FORMAT SOURCES
    # ---------------------------------

    sources = (
        format_sources_for_response(
            citation_map=rag_context[
                "citation_map"
            ],
            used_citations=(
                used_citations
            ),
        )
    )

    return {
        "generated": True,
        "reason": "success",
        "generated_text":
            answer.strip(),
        "sources": sources,
        "confidence": confidence,
        "citation_validation":
            validation,
        "citation_retry_used":
            retry_used,
    }