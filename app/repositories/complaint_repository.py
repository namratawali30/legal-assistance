from typing import Any

from app.database import database
from app.db.collections import (
    COMPLAINTS_COLLECTION,
    EVIDENCE_COLLECTION,
)


complaints_collection = database[COMPLAINTS_COLLECTION]
evidence_collection = database[EVIDENCE_COLLECTION]


async def create_complaint(
    complaint_data: dict[str, Any],
):
    result = await complaints_collection.insert_one(
        complaint_data
    )

    return result.inserted_id


async def get_complaint(
    complaint_id,
    user_id,
) -> dict[str, Any] | None:
    return await complaints_collection.find_one(
        {
            "_id": complaint_id,
            "user_id": user_id,
        }
    )


async def get_user_complaints(
    user_id,
) -> list[dict[str, Any]]:
    cursor = complaints_collection.find(
        {"user_id": user_id}
    ).sort(
        "updated_at",
        -1,
    )

    return await cursor.to_list(length=100)


async def create_evidence(
    evidence_data: dict[str, Any],
):
    result = await evidence_collection.insert_one(
        evidence_data
    )

    return result.inserted_id


async def get_complaint_evidence(
    complaint_id,
    user_id,
) -> list[dict[str, Any]]:
    cursor = evidence_collection.find(
        {
            "complaint_id": complaint_id,
            "user_id": user_id,
        }
    ).sort(
        "created_at",
        -1,
    )

    return await cursor.to_list(length=100)