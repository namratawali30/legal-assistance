from datetime import datetime, timezone
from typing import Any


def build_resource_document(
    title: str,
    category: str,
    description: str,
    url: str | None = None,
    organization: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    return {
        "title": title,
        "category": category,
        "description": description,
        "url": url,
        "organization": organization,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }