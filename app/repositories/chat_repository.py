from datetime import datetime, timezone
from typing import Any

from app.database import database
from app.db.collections import (
    CHAT_SESSIONS_COLLECTION,
    MESSAGES_COLLECTION,
)


chat_sessions_collection = database[CHAT_SESSIONS_COLLECTION]
messages_collection = database[MESSAGES_COLLECTION]


async def create_chat_session(
    session_data: dict[str, Any],
):
    result = await chat_sessions_collection.insert_one(
        session_data
    )

    return result.inserted_id


async def get_chat_session(
    session_id,
    user_id,
) -> dict[str, Any] | None:
    return await chat_sessions_collection.find_one(
        {
            "_id": session_id,
            "user_id": user_id,
        }
    )


async def get_user_chat_sessions(
    user_id,
) -> list[dict[str, Any]]:
    cursor = chat_sessions_collection.find(
        {
            "user_id": user_id,
        }
    ).sort(
        "updated_at",
        -1,
    )

    return await cursor.to_list(
        length=100
    )


async def update_chat_session(
    session_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    update_data["updated_at"] = datetime.now(
        timezone.utc
    )

    result = await chat_sessions_collection.update_one(
        {
            "_id": session_id,
            "user_id": user_id,
        },
        {
            "$set": update_data,
        },
    )

    if result.matched_count == 0:
        return None

    return await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )


async def delete_chat_session(
    session_id,
    user_id,
) -> bool:
    result = await chat_sessions_collection.delete_one(
        {
            "_id": session_id,
            "user_id": user_id,
        }
    )

    return result.deleted_count > 0


async def create_message(
    message_data: dict[str, Any],
):
    result = await messages_collection.insert_one(
        message_data
    )

    return result.inserted_id


async def get_session_messages(
    session_id,
) -> list[dict[str, Any]]:
    cursor = messages_collection.find(
        {
            "session_id": session_id,
        }
    ).sort(
        "created_at",
        1,
    )

    return await cursor.to_list(
        length=500
    )


async def delete_session_messages(
    session_id,
) -> int:
    result = await messages_collection.delete_many(
        {
            "session_id": session_id,
        }
    )

    return result.deleted_count