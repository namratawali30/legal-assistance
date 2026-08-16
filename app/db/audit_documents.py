from datetime import datetime, timezone
from typing import Any


def build_audit_log_document(
    action: str,
    user_id=None,
    resource_type: str | None = None,
    resource_id=None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "created_at": datetime.now(timezone.utc),
    }