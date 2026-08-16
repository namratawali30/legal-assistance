from typing import Any

from app.database import database
from app.db.collections import AUDIT_LOGS_COLLECTION


audit_logs_collection = database[AUDIT_LOGS_COLLECTION]


async def create_audit_log(
    audit_data: dict[str, Any],
):
    result = await audit_logs_collection.insert_one(
        audit_data
    )

    return result.inserted_id


async def get_user_audit_logs(
    user_id,
) -> list[dict[str, Any]]:
    cursor = audit_logs_collection.find(
        {
            "user_id": user_id,
        }
    ).sort(
        "created_at",
        -1,
    )

    return await cursor.to_list(length=200)