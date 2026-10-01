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
from app.rag.evidence_citation_guard import (
    extract_evidence_citations,
    validate_evidence_citations,
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
from app.services.complaint_evidence_context_service import (
    build_complaint_evidence_context,
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
        parts.append(f"Requested relief: {relief}")

    if incident_location:
        parts.append(f"Incident location: {incident_location}")

    return "\n".join(parts)


def empty_evidence_context() -> dict[str, Any]:
    return {
        "has_evidence": False,
        "context": "",
        "references": [],
        "included_count": 0,
        "skipped": [],
        "total_characters": 0,
        "complaint_id": None,
    }


async def load_evidence_context(
    complaint: dict[str, Any],
) -> dict[str, Any]:
    """
    Load evidence only when the complaint is a persisted
    complaint document with both ownership identifiers.

    Keeping this optional preserves compatibility with
    direct unit tests using plain complaint dictionaries.
    """

    complaint_id = complaint.get("_id")

    user_id = complaint.get("user_id")

    if complaint_id is None or user_id is None:
        return empty_evidence_context()

    return await build_complaint_evidence_context(
        complaint_id=complaint_id,
        user_id=user_id,
    )


def get_allowed_evidence_citations(
    evidence_context: dict[str, Any],
) -> list[str]:
    return [
        reference["citation_id"]
        for reference in evidence_context.get("references", [])
        if reference.get("citation_id")
    ]


def filter_used_evidence_references(
    evidence_context: dict[str, Any],
    used_citations: list[str],
) -> list[dict[str, Any]]:
    used = {citation.upper() for citation in used_citations}

    return [
        reference
        for reference in evidence_context.get("references", [])
        if str(reference.get("citation_id", "")).upper() in used
    ]


def citations_are_valid(
    legal_validation: dict[str, Any],
    used_legal_citations: list[str],
    evidence_validation: dict[str, Any],
) -> bool:
    # A grounded complaint must contain at least one
    # authoritative legal citation.
    if not legal_validation["valid"]:
        return False

    if not used_legal_citations:
        return False

    # Evidence citations are optional, but any that
    # appear must be valid.
    if not evidence_validation["valid"]:
        return False

    return True


async def generate_grounded_complaint(
    complaint: dict[str, Any],
    top_k: int = 5,
) -> dict[str, Any]:
    category = complaint.get("category")

    retrieval_query = build_complaint_retrieval_query(complaint)

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
            "evidence_references": [],
            "confidence": None,
            "citation_retry_used": False,
        }

    # ---------------------------------
    # 2. CONFIDENCE GATE
    # ---------------------------------

    confidence = evaluate_retrieval_confidence(results)

    if not confidence["accepted"]:
        return {
            "generated": False,
            "reason": "low_relevance",
            "generated_text": None,
            "sources": [],
            "evidence_references": [],
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

    if rag_context["source_count"] == 0:
        return {
            "generated": False,
            "reason": "no_valid_context",
            "generated_text": None,
            "sources": [],
            "evidence_references": [],
            "confidence": confidence,
            "citation_retry_used": False,
        }

    allowed_citations = rag_context["allowed_citations"]

    # ---------------------------------
    # 4. CONTROLLED EVIDENCE CONTEXT
    # ---------------------------------

    evidence_context = await load_evidence_context(complaint)

    allowed_evidence_citations = get_allowed_evidence_citations(evidence_context)

    # ---------------------------------
    # 5. GENERATE FIRST DRAFT
    # ---------------------------------

    user_prompt = build_complaint_prompt(
        complaint=complaint,
        context=rag_context["context"],
        allowed_citations=(allowed_citations),
        evidence_context=(evidence_context["context"]),
        allowed_evidence_citations=(allowed_evidence_citations),
    )

    answer = await generate_text(
        instructions=(COMPLAINT_SYSTEM_INSTRUCTIONS),
        input_text=user_prompt,
    )

    legal_validation = validate_citations(
        answer=answer,
        allowed_citations=(allowed_citations),
    )

    used_legal_citations = extract_citations(answer)

    evidence_validation = validate_evidence_citations(
        answer=answer,
        allowed_citations=(allowed_evidence_citations),
    )

    used_evidence_citations = extract_evidence_citations(answer)

    retry_used = False

    # ---------------------------------
    # 6. ONE COMBINED CITATION RETRY
    # ---------------------------------

    if not citations_are_valid(
        legal_validation=legal_validation,
        used_legal_citations=(used_legal_citations),
        evidence_validation=(evidence_validation),
    ):
        retry_used = True

        retry_prompt = build_complaint_retry_prompt(
            complaint=complaint,
            context=rag_context["context"],
            allowed_citations=(allowed_citations),
            previous_answer=answer,
            evidence_context=(evidence_context["context"]),
            allowed_evidence_citations=(allowed_evidence_citations),
        )

        answer = await generate_text(
            instructions=(
                COMPLAINT_SYSTEM_INSTRUCTIONS + "\n\n" + CITATION_RETRY_INSTRUCTIONS
            ),
            input_text=retry_prompt,
        )

        legal_validation = validate_citations(
            answer=answer,
            allowed_citations=(allowed_citations),
        )

        used_legal_citations = extract_citations(answer)

        evidence_validation = validate_evidence_citations(
            answer=answer,
            allowed_citations=(allowed_evidence_citations),
        )

        used_evidence_citations = extract_evidence_citations(answer)

    # ---------------------------------
    # 7. FAIL CLOSED
    # ---------------------------------

    if not citations_are_valid(
        legal_validation=legal_validation,
        used_legal_citations=(used_legal_citations),
        evidence_validation=(evidence_validation),
    ):
        return {
            "generated": False,
            "reason": "citation_validation_failed",
            "generated_text": None,
            "sources": [],
            "evidence_references": [],
            "confidence": confidence,
            # Preserve the existing key for
            # compatibility with current tests.
            "citation_validation": legal_validation,
            "evidence_citation_validation": evidence_validation,
            "citation_retry_used": retry_used,
        }

    # ---------------------------------
    # 8. FORMAT LEGAL SOURCES
    # ---------------------------------

    sources = format_sources_for_response(
        citation_map=rag_context["citation_map"],
        used_citations=(used_legal_citations),
    )

    # ---------------------------------
    # 9. FORMAT USED EVIDENCE REFERENCES
    # ---------------------------------

    evidence_references = filter_used_evidence_references(
        evidence_context=(evidence_context),
        used_citations=(used_evidence_citations),
    )

    return {
        "generated": True,
        "reason": "success",
        "generated_text": answer.strip(),
        "sources": sources,
        "evidence_references": evidence_references,
        "confidence": confidence,
        # Existing API preserved.
        "citation_validation": legal_validation,
        "evidence_citation_validation": evidence_validation,
        "citation_retry_used": retry_used,
        # Safe processing metadata only.
        # Raw evidence context is NOT returned.
        "evidence_context_summary": {
            "available": evidence_context.get(
                "has_evidence",
                False,
            ),
            "included_count": evidence_context.get(
                "included_count",
                0,
            ),
            "used_count": len(evidence_references),
            "skipped_count": len(
                evidence_context.get(
                    "skipped",
                    [],
                )
            ),
        },
    }
