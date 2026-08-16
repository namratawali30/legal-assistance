from datetime import datetime, timezone
from typing import Any


def build_chat_session_document(
    user_id,
    title: str,
    category: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    return {
        "user_id": user_id,
        "title": title,
        "category": category,
        "created_at": now,
        "updated_at": now,
    }


def build_message_document(
    session_id,
    user_id,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": datetime.now(timezone.utc),
    }