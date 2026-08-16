from app.database import database

from app.db.collections import (
    CHAT_SESSIONS_COLLECTION,
    MESSAGES_COLLECTION,
    USERS_COLLECTION,
)


async def create_indexes():
    users_collection = database[USERS_COLLECTION]
    chat_sessions_collection = database[CHAT_SESSIONS_COLLECTION]
    messages_collection = database[MESSAGES_COLLECTION]

    await users_collection.create_index(
        "email",
        unique=True,
    )

    await chat_sessions_collection.create_index(
        [
            ("user_id", 1),
            ("updated_at", -1),
        ]
    )

    await messages_collection.create_index(
        [
            ("session_id", 1),
            ("created_at", 1),
        ]
    )