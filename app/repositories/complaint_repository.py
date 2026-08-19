from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.database import database
from app.db.collections import (
    COMPLAINTS_COLLECTION,
)


complaints_collection = database[
    COMPLAINTS_COLLECTION
]


def to_object_id(value):
    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(
            str(value)
        )

    except (
        InvalidId,
        TypeError,
        ValueError,
    ):
        return None


async def create_complaint(
    complaint_data: dict[str, Any],
):
    result = (
        await complaints_collection.insert_one(
            complaint_data
        )
    )

    return result.inserted_id


async def get_complaint(
    complaint_id,
    user_id,
) -> dict[str, Any] | None:
    object_id = to_object_id(
        complaint_id
    )

    if object_id is None:
        return None

    return await complaints_collection.find_one(
        {
            "_id": object_id,
            "user_id": user_id,
        }
    )


async def get_user_complaints(
    user_id,
) -> list[dict[str, Any]]:
    cursor = complaints_collection.find(
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


async def update_complaint(
    complaint_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    object_id = to_object_id(
        complaint_id
    )

    if object_id is None:
        return None

    safe_update_data = dict(
        update_data
    )

    safe_update_data[
        "updated_at"
    ] = datetime.now(
        timezone.utc
    )

    result = (
        await complaints_collection.update_one(
            {
                "_id": object_id,
                "user_id": user_id,
            },
            {
                "$set":
                    safe_update_data,
            },
        )
    )

    if result.matched_count == 0:
        return None

    return await get_complaint(
        complaint_id=object_id,
        user_id=user_id,
    )


async def delete_complaint(
    complaint_id,
    user_id,
) -> bool:
    object_id = to_object_id(
        complaint_id
    )

    if object_id is None:
        return False

    result = (
        await complaints_collection.delete_one(
            {
                "_id": object_id,
                "user_id": user_id,
            }
        )
    )

    return (
        result.deleted_count > 0
    )