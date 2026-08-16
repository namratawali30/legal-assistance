from typing import Any

from app.db.complaint_documents import (
    build_complaint_document,
    build_evidence_document,
)
from app.repositories.complaint_repository import (
    create_complaint,
    create_evidence,
    get_complaint,
    get_complaint_evidence,
    get_user_complaints,
)


async def create_user_complaint(
    user_id,
    category: str,
    title: str,
    description: str,
):
    complaint_data = build_complaint_document(
        user_id=user_id,
        category=category,
        title=title,
        description=description,
    )

    return await create_complaint(complaint_data)


async def find_user_complaint(
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
    return await get_user_complaints(user_id)


async def add_evidence(
    complaint_id,
    user_id,
    original_filename: str,
    content_type: str,
    file_size: int,
    storage_path: str,
):
    evidence_data = build_evidence_document(
        complaint_id=complaint_id,
        user_id=user_id,
        original_filename=original_filename,
        content_type=content_type,
        file_size=file_size,
        storage_path=storage_path,
    )

    return await create_evidence(evidence_data)


async def list_complaint_evidence(
    complaint_id,
    user_id,
):
    return await get_complaint_evidence(
        complaint_id=complaint_id,
        user_id=user_id,
    )