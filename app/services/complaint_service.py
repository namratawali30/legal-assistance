from datetime import date, datetime, timezone
from typing import Any

from app.db.complaint_documents import (
    build_complaint_document,
)
from app.rag.citation_guard import (
    extract_citations,
    validate_citations,
)
from app.repositories.complaint_repository import (
    create_complaint,
    delete_complaint,
    get_complaint,
    get_user_complaints,
    update_complaint,
)


IMMUTABLE_FIELDS = {
    "_id",
    "user_id",
    "created_at",
    "generated_at",
    "finalized_at",
    "generated_text",
    "sources",
    "status",
}


class ComplaintStateError(Exception):
    """Base exception for invalid complaint state operations."""


class ComplaintFinalizedError(ComplaintStateError):
    """Raised when attempting to modify a finalized complaint."""


class ComplaintNotGeneratedError(ComplaintStateError):
    """Raised when generated text does not yet exist."""


class ComplaintFinalizationError(ComplaintStateError):
    """Raised when a complaint cannot safely be finalized."""


def serialize_update_value(
    field_name: str,
    value,
):
    if field_name == "incident_date":
        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):
            return (
                value
                .date()
                .isoformat()
            )

        if isinstance(
            value,
            date,
        ):
            return value.isoformat()

    return value


async def create_complaint_draft(
    user_id,
    complaint_data: dict[str, Any],
) -> dict[str, Any] | None:
    category = complaint_data[
        "category"
    ]

    if hasattr(
        category,
        "value",
    ):
        category = category.value

    document = build_complaint_document(
        user_id=user_id,

        title=complaint_data[
            "title"
        ],

        category=category,

        complainant_name=complaint_data[
            "complainant_name"
        ],

        complainant_address=complaint_data.get(
            "complainant_address"
        ),

        complainant_contact=complaint_data.get(
            "complainant_contact"
        ),

        respondent_name=complaint_data[
            "respondent_name"
        ],

        respondent_address=complaint_data.get(
            "respondent_address"
        ),

        incident_date=complaint_data.get(
            "incident_date"
        ),

        incident_location=complaint_data.get(
            "incident_location"
        ),

        facts=complaint_data[
            "facts"
        ],

        relief_requested=complaint_data.get(
            "relief_requested"
        ),

        additional_details=complaint_data.get(
            "additional_details"
        ),
    )

    complaint_id = await create_complaint(
        document
    )

    return await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )


async def find_complaint(
    complaint_id,
    user_id,
) -> dict[str, Any] | None:
    return await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )


async def list_user_complaints(
    user_id,
) -> list[dict[str, Any]]:
    return await get_user_complaints(
        user_id=user_id
    )


async def update_complaint_draft(
    complaint_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )

    # Finalized complaints become immutable.
    if current_status == "finalized":
        raise ComplaintFinalizedError(
            "Finalized complaints cannot be edited."
        )

    cleaned_update = {}

    for field_name, value in update_data.items():
        if field_name in IMMUTABLE_FIELDS:
            continue

        if (
            field_name == "category"
            and hasattr(
                value,
                "value",
            )
        ):
            value = value.value

        cleaned_update[
            field_name
        ] = serialize_update_value(
            field_name,
            value,
        )

    if not cleaned_update:
        return existing

    # Any structured edit after generation means
    # the saved complaint has been modified.
    if current_status in {
        "generated",
        "edited",
    }:
        cleaned_update[
            "status"
        ] = "edited"

    return await update_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
        update_data=cleaned_update,
    )


async def edit_generated_complaint_text(
    complaint_id,
    user_id,
    generated_text: str,
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )

    if current_status == "finalized":
        raise ComplaintFinalizedError(
            "Finalized complaints cannot be edited."
        )

    if current_status == "draft":
        raise ComplaintNotGeneratedError(
            "Generate the complaint before editing "
            "the generated text."
        )

    if not existing.get(
        "generated_text"
    ):
        raise ComplaintNotGeneratedError(
            "Generated complaint text is not available."
        )

    cleaned_text = generated_text.strip()

    if not cleaned_text:
        raise ComplaintStateError(
            "Generated complaint text cannot be empty."
        )

    # Users may edit wording, but they must not
    # invent citation identifiers that were never
    # attached to this generated complaint.
    allowed_citations = [
        source.get("citation_id")
        for source in existing.get(
            "sources",
            [],
        )
        if source.get(
            "citation_id"
        )
    ]

    used_citations = extract_citations(
        cleaned_text
    )

    invalid_citations = [
        citation
        for citation in used_citations
        if citation not in allowed_citations
    ]

    if invalid_citations:
        raise ComplaintStateError(
            "The edited complaint contains "
            "unknown legal source citations."
        )

    return await update_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
        update_data={
            "generated_text":
                cleaned_text,

            "status":
                "edited",
        },
    )


async def finalize_complaint(
    complaint_id,
    user_id,
    confirm: bool,
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )

    if current_status == "finalized":
        raise ComplaintFinalizedError(
            "Complaint has already been finalized."
        )

    if not confirm:
        raise ComplaintFinalizationError(
            "Explicit confirmation is required "
            "before finalizing the complaint."
        )

    if current_status not in {
        "generated",
        "edited",
    }:
        raise ComplaintNotGeneratedError(
            "Generate the complaint before finalizing it."
        )

    generated_text = (
        existing.get(
            "generated_text"
        )
        or ""
    ).strip()

    if not generated_text:
        raise ComplaintNotGeneratedError(
            "Generated complaint text is not available."
        )

    sources = existing.get(
        "sources",
        [],
    )

    if not sources:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized "
            "without authoritative legal sources."
        )

    allowed_citations = [
        source.get(
            "citation_id"
        )
        for source in sources
        if source.get(
            "citation_id"
        )
    ]

    if not allowed_citations:
        raise ComplaintFinalizationError(
            "The complaint does not contain valid "
            "legal source metadata."
        )

    citation_validation = validate_citations(
        answer=generated_text,
        allowed_citations=allowed_citations,
    )

    used_citations = extract_citations(
        generated_text
    )

    if (
        not citation_validation[
            "valid"
        ]
        or not used_citations
    ):
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized "
            "because its legal citations are missing "
            "or invalid."
        )

    finalized_at = datetime.now(
        timezone.utc
    )

    return await update_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
        update_data={
            "status":
                "finalized",

            "finalized_at":
                finalized_at,
        },
    )


async def remove_complaint(
    complaint_id,
    user_id,
) -> bool:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return False

    if (
        existing.get(
            "status",
            "draft",
        )
        == "finalized"
    ):
        raise ComplaintFinalizedError(
            "Finalized complaints cannot be deleted."
        )

    return await delete_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )