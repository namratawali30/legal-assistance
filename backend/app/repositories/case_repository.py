from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from bson.errors import InvalidId

from app.database import database
from app.db.collections import CASES_COLLECTION

cases_collection = database[CASES_COLLECTION]


def to_object_id(value):
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError, ValueError):
        return None


async def create_case(case_data: dict[str, Any]) -> dict[str, Any]:
    document = dict(case_data)
    now = datetime.now(timezone.utc)
    document.setdefault("created_at", now)
    document.setdefault("updated_at", now)
    document.setdefault("status", "intake")
    document.setdefault("chat_session_ids", [])
    document.setdefault("evidence_ids", [])
    document.setdefault("complaint_ids", [])
    document.setdefault("reminders", [])
    document.setdefault("activity_log", [])

    result = await cases_collection.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def get_case(case_id: str, user_id: str) -> dict[str, Any] | None:
    object_id = to_object_id(case_id)
    query_ids = [str(case_id)]
    if object_id is not None:
        query_ids.append(object_id)

    case = await cases_collection.find_one({"_id": {"$in": query_ids}})
    if not case:
        return None

    # Check ownership or reviewer access
    owner_id = str(case.get("user_id"))
    reviewers = [str(r.get("reviewer_id")) for r in case.get("reviewer_access", [])]
    if owner_id != str(user_id) and str(user_id) not in reviewers:
        return None

    return case


async def get_user_cases(user_id: str) -> list[dict[str, Any]]:
    cursor = cases_collection.find(
        {"$or": [{"user_id": str(user_id)}, {"reviewer_access.reviewer_id": str(user_id)}]}
    ).sort("updated_at", -1)
    return await cursor.to_list(length=100)


async def update_case(case_id: str, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    case = await get_case(case_id, user_id)
    if not case:
        return None

    now = datetime.now(timezone.utc)
    update_fields = dict(update_data)
    update_fields["updated_at"] = now

    query = {"_id": case["_id"]}
    await cases_collection.update_one(query, {"$set": update_fields})
    return await cases_collection.find_one(query)


async def add_case_activity(case_id: str, actor_id: str, action: str, details: str | None = None) -> None:
    object_id = to_object_id(case_id)
    query = {"_id": object_id if object_id else case_id}
    activity = {
        "timestamp": datetime.now(timezone.utc),
        "action": action,
        "actor_id": str(actor_id),
        "details": details,
    }
    await cases_collection.update_one(query, {"$push": {"activity_log": activity}})


async def delete_case(case_id: str, user_id: str) -> bool:
    object_id = to_object_id(case_id)
    query_ids = [str(case_id)]
    if object_id is not None:
        query_ids.append(object_id)

    result = await cases_collection.delete_one(
        {"_id": {"$in": query_ids}, "user_id": str(user_id)}
    )
    return result.deleted_count > 0
