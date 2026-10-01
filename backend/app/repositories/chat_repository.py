from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from bson.errors import InvalidId

from app.database import database
from app.db.collections import (
    CHAT_SESSIONS_COLLECTION,
    MESSAGES_COLLECTION,
)

chat_sessions_collection = database[CHAT_SESSIONS_COLLECTION]
messages_collection = database[MESSAGES_COLLECTION]


def to_object_id(value):
    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError, ValueError):
        return None


async def create_chat_session(
    session_data: dict[str, Any],
):
    # PyMongo may add _id to the supplied document.
    # Never let the repository mutate caller-owned state.
    document = dict(session_data)

    result = await chat_sessions_collection.insert_one(document)

    return result.inserted_id


async def get_chat_session(
    session_id,
    user_id,
):
    object_id = to_object_id(session_id)
    query_ids = [str(session_id)]
    if object_id is not None:
        query_ids.append(object_id)

    session = await chat_sessions_collection.find_one({"_id": {"$in": query_ids}})
    if not session:
        return None

    if str(session.get("user_id")) != str(user_id):
        return None

    return session


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

    return await cursor.to_list(length=100)


async def update_chat_session(
    session_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    object_id = to_object_id(session_id)

    if object_id is None:
        return None

    safe_update_data = dict(update_data)

    # Repository-managed identity/history fields
    # cannot be rewritten by a caller.
    for field_name in (
        "_id",
        "user_id",
        "created_at",
    ):
        safe_update_data.pop(
            field_name,
            None,
        )

    safe_update_data["updated_at"] = datetime.now(timezone.utc)

    result = await chat_sessions_collection.update_one(
        {
            "_id": object_id,
            "user_id": user_id,
        },
        {
            "$set": safe_update_data,
        },
    )

    if result.matched_count == 0:
        return None

    return await get_chat_session(
        session_id=object_id,
        user_id=user_id,
    )


async def delete_chat_session(
    session_id,
    user_id,
) -> bool:
    object_id = to_object_id(session_id)

    if object_id is None:
        return False

    result = await chat_sessions_collection.delete_one(
        {
            "_id": object_id,
            "user_id": user_id,
        }
    )

    return result.deleted_count > 0


async def create_message(
    message_data: dict[str, Any],
):
    # Avoid PyMongo adding _id to caller-owned state.
    document = dict(message_data)

    result = await messages_collection.insert_one(document)

    return result.inserted_id


async def get_session_messages(
    session_id,
    user_id=None,
) -> list[dict[str, Any]]:
    object_id = to_object_id(session_id)

    if object_id is None:
        return []

    query: dict[str, Any] = {
        "session_id": object_id,
    }

    if user_id is not None:
        query["user_id"] = user_id

    cursor = messages_collection.find(query).sort(
        "created_at",
        1,
    )

    return await cursor.to_list(length=500)


async def delete_session_messages(
    session_id,
    user_id=None,
) -> int:
    object_id = to_object_id(session_id)

    if object_id is None:
        return 0

    query: dict[str, Any] = {
        "session_id": object_id,
    }

    if user_id is not None:
        query["user_id"] = user_id

    result = await messages_collection.delete_many(query)

    return result.deleted_count


async def get_message_by_id(
    message_id,
    session_id,
    user_id,
) -> dict[str, Any] | None:
    message_object_id = to_object_id(message_id)

    session_object_id = to_object_id(session_id)

    if message_object_id is None or session_object_id is None:
        return None

    return await messages_collection.find_one(
        {
            "_id": message_object_id,
            "session_id": session_object_id,
            "user_id": user_id,
        }
    )


async def update_message(
    message_id,
    session_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    message_object_id = to_object_id(message_id)

    session_object_id = to_object_id(session_id)

    if message_object_id is None or session_object_id is None:
        return None

    safe_update_data = dict(update_data)

    for field_name in (
        "_id",
        "session_id",
        "user_id",
        "created_at",
    ):
        safe_update_data.pop(
            field_name,
            None,
        )

    safe_update_data["updated_at"] = datetime.now(timezone.utc)

    result = await messages_collection.update_one(
        {
            "_id": message_object_id,
            "session_id": session_object_id,
            "user_id": user_id,
        },
        {
            "$set": safe_update_data,
        },
    )

    if result.matched_count == 0:
        return None

    return await get_message_by_id(
        message_id=message_object_id,
        session_id=session_object_id,
        user_id=user_id,
    )
