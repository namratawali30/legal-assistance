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
    update_complaint,
)


class ComplaintGenerationError(
    Exception
):
    pass


class ComplaintAlreadyGeneratedError(
    ComplaintGenerationError
):
    pass


class ComplaintInsufficientContextError(
    ComplaintGenerationError
):
    pass


class ComplaintLLMUnavailableError(
    ComplaintGenerationError
):
    pass


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
    if complaint.get(
        "status",
        "draft",
    ) == "finalized":
        raise ComplaintFinalizedGenerationError(
            "Finalized complaints cannot be regenerated."
        )

    existing_text = complaint.get(
        "generated_text"
    )

    if (
        existing_text
        and not regenerate
    ):
        raise ComplaintAlreadyGeneratedError(
            "Complaint has already been generated. "
            "Set regenerate=true to replace it."
        )

    try:
        result = (
            await generate_grounded_complaint(
                complaint=complaint,
                top_k=5,
            )
        )

    except LLMServiceError as exc:
        raise ComplaintLLMUnavailableError(
            "Complaint generation service is "
            "temporarily unavailable."
        ) from exc

    if not result[
        "generated"
    ]:
        raise ComplaintInsufficientContextError(
            "Sufficient authoritative legal material "
            "could not be retrieved to safely generate "
            "this complaint."
        )

    update_data = {
        "generated_text":
            result[
                "generated_text"
            ],

        "sources":
            result[
                "sources"
            ],

        "status":
            "generated",

        "generated_at":
            datetime.now(
                timezone.utc
            ),
    }

    return await update_complaint(
        complaint_id=complaint["_id"],
        user_id=user_id,
        update_data=update_data,
    )
class ComplaintFinalizedGenerationError(
    ComplaintGenerationError
):
    pass