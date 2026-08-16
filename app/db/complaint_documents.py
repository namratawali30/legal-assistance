from datetime import datetime, timezone
from typing import Any


def build_complaint_document(
    user_id,
    category: str,
    title: str,
    description: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    return {
        "user_id": user_id,
        "category": category,
        "title": title,
        "description": description,
        "status": "draft",
        "generated_draft": None,
        "created_at": now,
        "updated_at": now,
    }


def build_evidence_document(
    complaint_id,
    user_id,
    original_filename: str,
    content_type: str,
    file_size: int,
    storage_path: str,
) -> dict[str, Any]:
    return {
        "complaint_id": complaint_id,
        "user_id": user_id,
        "original_filename": original_filename,
        "content_type": content_type,
        "file_size": file_size,
        "storage_path": storage_path,
        "created_at": datetime.now(timezone.utc),
    }