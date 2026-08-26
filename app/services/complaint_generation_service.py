from datetime import datetime, timezone
from typing import Any

from app.rag.complaint_generator import (
    generate_grounded_complaint,
)
from app.rag.llm_client import (
    LLMServiceError,
)
from app.repositories.complaint_repository import (
    get_complaint,
    update_complaint_if_unchanged,
)


class ComplaintGenerationError(Exception):
    pass


class ComplaintAlreadyGeneratedError(ComplaintGenerationError):
    pass


class ComplaintGenerationConflictError(ComplaintAlreadyGeneratedError):
    """
    Raised when the complaint changes while generation
    or regeneration is in progress.

    It subclasses ComplaintAlreadyGeneratedError so the
    existing conflict handling remains compatible.
    """


class ComplaintInsufficientContextError(ComplaintGenerationError):
    pass


class ComplaintLLMUnavailableError(ComplaintGenerationError):
    pass


class ComplaintFinalizedGenerationError(ComplaintGenerationError):
    pass

class ComplaintGenerationPersistenceError(ComplaintGenerationError):
    """
    Raised when a generated complaint cannot be
    persisted or its persistence cannot be confirmed.
    """

def get_complaint_revision(
    complaint: dict[str, Any],
) -> int:
    try:
        revision = int(
            complaint.get(
                "revision",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        revision,
        0,
    )


async def generate_complaint_for_user(
    complaint_id,
    user_id,
    regenerate: bool = False,
) -> dict[str, Any] | None:
    complaint = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not complaint:
        return None

    current_status = complaint.get(
        "status",
        "draft",
    )

    if current_status == "finalized":
        raise ComplaintFinalizedGenerationError(
            "Finalized complaints cannot be regenerated."
        )

    expected_revision = get_complaint_revision(complaint)

    existing_text = complaint.get("generated_text")

    if existing_text and not regenerate:
        raise ComplaintAlreadyGeneratedError(
            "Complaint has already been generated. "
            "Set regenerate=true to replace it."
        )

    try:
        result = await generate_grounded_complaint(
            complaint=complaint,
            top_k=5,
        )

    except LLMServiceError as exc:
        raise ComplaintLLMUnavailableError(
            "Complaint generation service is " "temporarily unavailable."
        ) from exc

    if not result["generated"]:
        raise ComplaintInsufficientContextError(
            "Sufficient authoritative legal material "
            "could not be retrieved to safely generate "
            "this complaint."
        )

    update_data = {
        "generated_text": result["generated_text"],
        "sources": result["sources"],
        # Snapshot only safe metadata describing
        # evidence actually cited by the generated
        # complaint. Raw extracted_text is never copied.
        "evidence_references": result.get(
            "evidence_references",
            [],
        ),
        "status": "generated",
        "generated_at": datetime.now(timezone.utc),
        # A regenerated complaint is not finalized.
        "finalized_at": None,
    }

    try:
        updated = await update_complaint_if_unchanged(
            complaint_id=complaint["_id"],
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=current_status,
            update_data=update_data,
        )

    except Exception as exc:
        raise ComplaintGenerationPersistenceError(
            "Complaint generation completed, "
            "but the generated result could not "
            "be saved safely."
        ) from exc

    if updated:
        return updated

    # CAS failed. Determine whether the complaint was
    # finalized or simply changed concurrently.
    latest = await get_complaint(
        complaint_id=complaint["_id"],
        user_id=user_id,
    )

    if not latest:
        return None

    if (
        latest.get(
            "status",
            "draft",
        )
        == "finalized"
    ):
        raise ComplaintFinalizedGenerationError(
            "The complaint was finalized while " "generation was in progress."
        )

    raise ComplaintGenerationConflictError(
        "The complaint changed while generation "
        "was in progress. Reload it and retry."
    )
