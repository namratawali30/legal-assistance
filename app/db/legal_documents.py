from datetime import datetime, timezone
from typing import Any


def build_legal_document(
    title: str,
    category: str,
    source: str,
    description: str | None = None,
    document_type: str = "legal_reference",
    version: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    return {
        "title": title,
        "category": category,
        "source": source,
        "description": description,
        "document_type": document_type,
        "version": version,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }