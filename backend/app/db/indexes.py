from app.database import database

from app.db.collections import (
    CHAT_SESSIONS_COLLECTION,
    COMPLAINTS_COLLECTION,
    MESSAGES_COLLECTION,
    REFRESH_TOKENS_COLLECTION,
    USERS_COLLECTION,
)


async def create_indexes():
    users_collection = database[USERS_COLLECTION]

    chat_sessions_collection = database[CHAT_SESSIONS_COLLECTION]

    messages_collection = database[MESSAGES_COLLECTION]

    complaints_collection = database[COMPLAINTS_COLLECTION]

    # =====================================================
    # USERS
    # =====================================================

    await users_collection.create_index(
        "email",
        unique=True,
    )

    # =====================================================
    # CHAT SESSIONS
    # =====================================================
    #
    # Supports:
    #   find({"user_id": ...})
    #       .sort("updated_at", -1)
    # =====================================================

    await chat_sessions_collection.create_index(
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ]
    )

    # =====================================================
    # MESSAGES
    # =====================================================
    #
    # Supports:
    #   find({"session_id": ...})
    #       .sort("created_at", 1)
    #
    # Also supports delete_many(session_id).
    # =====================================================

    await messages_collection.create_index(
        [
            (
                "session_id",
                1,
            ),
            (
                "created_at",
                1,
            ),
        ]
    )

    # =====================================================
    # COMPLAINT LISTING
    # =====================================================
    #
    # Supports:
    #   find({"user_id": ...})
    #       .sort("updated_at", -1)
    # =====================================================

    await complaints_collection.create_index(
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ]
    )

    # =====================================================
    # FINALIZED EVIDENCE REFERENCE LOOKUP
    # =====================================================
    #
    # Supports the lifecycle check that determines
    # whether finalized complaint text cites a given
    # evidence record.
    #
    # evidence_references is an array, so MongoDB will
    # maintain this as a multikey index automatically.
    # =====================================================

    await complaints_collection.create_index(
        [
            (
                "user_id",
                1,
            ),
            (
                "status",
                1,
            ),
            (
                "evidence_references.evidence_id",
                1,
            ),
        ]
    )

    # =====================================================
    # REFRESH TOKENS
    # =====================================================

    refresh_tokens_collection = database[REFRESH_TOKENS_COLLECTION]

    # Fast lookup by token hash
    await refresh_tokens_collection.create_index(
        "token_hash",
        unique=True,
    )

    # Revoke all tokens for a user
    await refresh_tokens_collection.create_index(
        "user_id",
    )

    # TTL index — MongoDB automatically removes expired
    # documents, but we also check expiry in queries.
    await refresh_tokens_collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
    )
