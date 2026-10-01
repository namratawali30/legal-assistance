from datetime import datetime, timezone
from typing import Any


def build_chat_session_document(
    user_id,
    title: str,
    category: str,
    case_context: dict[str, Any] | None = None,
    clarification_count: int = 0,
    answer_mode: str = "simple",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    return {
        "user_id": user_id,
        "title": title,
        "category": category,
        "case_context": dict(case_context or {}),
        "clarification_count": clarification_count,
        "answer_mode": answer_mode,
        "created_at": now,
        "updated_at": now,
    }



def build_message_document(
    session_id,
    user_id,
    role: str,
    content: str,
    sources: list[dict] | None = None,
    status: str = "completed",
    message_type: str = "answer",
    suggested_options: list[str] | None = None,
    category_notice: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    doc = {
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "sources": list(sources or []),
        "created_at": now,
        "updated_at": now,
        "status": status,
        "message_type": message_type,
    }
    if suggested_options is not None:
        doc["suggested_options"] = suggested_options
    if category_notice is not None:
        doc["category_notice"] = category_notice
    return doc


