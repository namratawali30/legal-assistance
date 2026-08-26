from typing import Any

from app.rag.evidence_context import (
    DEFAULT_MAX_CHARS_PER_ITEM,
    DEFAULT_MAX_EVIDENCE_ITEMS,
    DEFAULT_MAX_TOTAL_CHARS,
    build_evidence_context,
)
from app.repositories.complaint_repository import (
    get_complaint,
)
from app.repositories.evidence_repository import (
    get_user_evidence,
)


class ComplaintEvidenceContextError(Exception):
    """Base error for complaint evidence context."""


class ComplaintEvidenceNotFoundError(
    ComplaintEvidenceContextError
):
    """Raised when the complaint is missing or not owned."""


async def build_complaint_evidence_context(
    complaint_id,
    user_id,
    max_items: int = DEFAULT_MAX_EVIDENCE_ITEMS,
    max_chars_per_item: int = (
        DEFAULT_MAX_CHARS_PER_ITEM
    ),
    max_total_chars: int = (
        DEFAULT_MAX_TOTAL_CHARS
    ),
) -> dict[str, Any]:
    """
    Load only evidence belonging to the authenticated
    user's complaint and build bounded factual context.
    """

    complaint = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not complaint:
        raise ComplaintEvidenceNotFoundError(
            "Complaint not found."
        )

    evidence_records = await get_user_evidence(
        user_id=user_id,
        complaint_id=complaint[
            "_id"
        ],
    )

    result = build_evidence_context(
        evidence_records=evidence_records,
        max_items=max_items,
        max_chars_per_item=max_chars_per_item,
        max_total_chars=max_total_chars,
    )

    result[
        "complaint_id"
    ] = str(
        complaint[
            "_id"
        ]
    )

    return result