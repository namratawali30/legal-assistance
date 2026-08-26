from datetime import datetime, timezone
from typing import Any


def build_user_document(
    email: str,
    full_name: str,
    password_hash: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    normalized_email = email.strip().lower()

    return {
        "email": normalized_email,
        "full_name": full_name.strip(),
        "password_hash": password_hash,
        "role": "user",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
