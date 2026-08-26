from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.database import database
from app.db.collections import (
    USERS_COLLECTION,
)

users_collection = database[USERS_COLLECTION]


def normalize_email(
    email: str,
) -> str:
    return email.strip().lower()


async def get_user_by_email(
    email: str,
) -> dict[str, Any] | None:
    normalized_email = normalize_email(email)

    return await users_collection.find_one({"email": normalized_email})


async def get_user_by_id(
    user_id: str,
) -> dict[str, Any] | None:
    try:
        object_id = ObjectId(user_id)

    except (
        InvalidId,
        TypeError,
    ):
        return None

    return await users_collection.find_one({"_id": object_id})


async def create_user(
    user_data: dict[str, Any],
):
    result = await users_collection.insert_one(user_data)

    return result.inserted_id
