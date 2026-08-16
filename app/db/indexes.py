from app.database import database
from app.db.collections import (
    USERS_COLLECTION,
    CHAT_SESSIONS_COLLECTION,
    MESSAGES_COLLECTION,
    COMPLAINTS_COLLECTION,
    EVIDENCE_COLLECTION,
    RESOURCES_COLLECTION,
    LEGAL_DOCUMENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
)


async def create_indexes() -> None:
    await database[USERS_COLLECTION].create_index(
        "email",
        unique=True,
    )

    await database[CHAT_SESSIONS_COLLECTION].create_index(
        "user_id"
    )

    await database[MESSAGES_COLLECTION].create_index(
        "session_id"
    )

    await database[COMPLAINTS_COLLECTION].create_index(
        "user_id"
    )

    await database[EVIDENCE_COLLECTION].create_index(
        "complaint_id"
    )

    await database[RESOURCES_COLLECTION].create_index(
        "category"
    )

    await database[LEGAL_DOCUMENTS_COLLECTION].create_index(
        "category"
    )

    await database[AUDIT_LOGS_COLLECTION].create_index(
        "user_id"
    )