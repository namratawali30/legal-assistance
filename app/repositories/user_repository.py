from typing import Any

from app.database import database
from app.db.collections import USERS_COLLECTION


users_collection = database[USERS_COLLECTION]


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    return await users_collection.find_one(
        {"email": email}
    )


async def get_user_by_id(user_id) -> dict[str, Any] | None:
    return await users_collection.find_one(
        {"_id": user_id}
    )


async def create_user(user_data: dict[str, Any]) -> Any:
    result = await users_collection.insert_one(user_data)

    return result.inserted_id