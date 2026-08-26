from datetime import datetime, timezone, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.database import database
from app.db.collections import (
    COMPLAINTS_COLLECTION,
)

complaints_collection = database[COMPLAINTS_COLLECTION]


def to_object_id(value):
    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(str(value))

    except (
        InvalidId,
        TypeError,
        ValueError,
    ):
        return None


def normalize_revision(
    value,
) -> int:
    """
    Normalize legacy/missing complaint revisions.

    Older complaint records do not have a revision field,
    so they are treated as revision 0.
    """

    try:
        revision = int(value or 0)

    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        revision,
        0,
    )


async def create_complaint(
    complaint_data: dict[str, Any],
):
    document = dict(complaint_data)

    # New complaints begin at revision zero.
    #
    # Every subsequent repository mutation increments
    # this value atomically.
    document.setdefault(
        "revision",
        0,
    )

    result = await complaints_collection.insert_one(document)

    return result.inserted_id


async def get_complaint(
    complaint_id,
    user_id,
) -> dict[str, Any] | None:
    object_id = to_object_id(complaint_id)

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

    return await cursor.to_list(length=100)


async def update_complaint(
    complaint_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Perform a normal complaint update.

    Every successful mutation increments revision so any
    stale CAS reader can detect that the complaint changed.

    This preserves the existing repository interface.
    """

    object_id = to_object_id(complaint_id)

    if object_id is None:
        return None

    safe_update_data = dict(update_data)
    for field_name in (
        "_id",
        "user_id",
        "created_at",
        "revision",
    ):
        safe_update_data.pop(
            field_name,
            None,
        )
    

    # revision is repository-managed and must never be
    # directly supplied by callers.
    safe_update_data.pop(
        "revision",
        None,
    )

    safe_update_data["updated_at"] = datetime.now(timezone.utc)

    return await complaints_collection.find_one_and_update(
        {
            "_id": object_id,
            "user_id": user_id,
        },
        {
            "$set": safe_update_data,
            "$inc": {
                "revision": 1,
            },
        },
        return_document=(ReturnDocument.AFTER),
    )


async def update_complaint_if_unchanged(
    complaint_id,
    user_id,
    expected_revision: int,
    expected_status: str,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Atomically update a complaint only when the caller's
    snapshot is still current.

    This is the complaint compare-and-set primitive used
    to prevent races between:

    - structured edits
    - generated-text edits
    - generation/regeneration
    - finalization

    Returns the updated complaint on success.

    Returns None when:
    - complaint no longer exists, or
    - status changed, or
    - revision changed.
    """

    object_id = to_object_id(
        complaint_id
    )

    if object_id is None:
        return None

    normalized_expected_revision = normalize_revision(
        expected_revision
    )

    query: dict[str, Any] = {
        "_id": object_id,
        "user_id": user_id,
        "status": expected_status,
    }

    if normalized_expected_revision == 0:
        query["$or"] = [
            {
                "revision": {
                    "$exists": False,
                }
            },
            {
                "revision": 0,
            },
        ]

    else:
        query["revision"] = (
            normalized_expected_revision
        )

    safe_update_data = dict(
        update_data
    )

    for field_name in (
        "_id",
        "user_id",
        "created_at",
        "revision",
    ):
        safe_update_data.pop(
            field_name,
            None,
        )

    safe_update_data[
        "updated_at"
    ] = datetime.now(
        timezone.utc
    )

    return await complaints_collection.find_one_and_update(
        query,
        {
            "$set": safe_update_data,
            "$inc": {
                "revision": 1,
            },
        },
        return_document=ReturnDocument.AFTER,
    )

async def acquire_complaint_lifecycle_lock(
    complaint_id,
    user_id,
    lock_token: str,
    operation: str,
    lease_seconds: int = 300,
) -> dict[str, Any] | None:
    """
    Atomically acquire a short-lived complaint lifecycle
    lease.

    Used to coordinate operations that must not overlap
    with complaint deletion, especially linked evidence
    creation.

    Lock metadata deliberately does not change revision
    or updated_at because it is internal coordination
    state, not user-visible complaint content.
    """

    object_id = to_object_id(complaint_id)

    if object_id is None:
        return None

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(seconds=lease_seconds)

    return await complaints_collection.find_one_and_update(
        {
            "_id": object_id,
            "user_id": user_id,
            "$or": [
                {
                    "lifecycle_lock_token": {
                        "$exists": False,
                    }
                },
                {
                    "lifecycle_lock_token": None,
                },
                {
                    "lifecycle_lock_expires_at": {
                        "$lte": now,
                    }
                },
            ],
        },
        {
            "$set": {
                "lifecycle_lock_token": lock_token,
                "lifecycle_lock_operation": operation,
                "lifecycle_lock_acquired_at": now,
                "lifecycle_lock_expires_at": expires_at,
            }
        },
        return_document=(ReturnDocument.AFTER),
    )


async def release_complaint_lifecycle_lock(
    complaint_id,
    user_id,
    lock_token: str,
) -> bool:
    """
    Release a complaint lifecycle lease only when the
    caller still owns the exact token.
    """

    object_id = to_object_id(complaint_id)

    if object_id is None:
        return False

    result = await complaints_collection.update_one(
        {
            "_id": object_id,
            "user_id": user_id,
            "lifecycle_lock_token": lock_token,
        },
        {
            "$unset": {
                "lifecycle_lock_token": "",
                "lifecycle_lock_operation": "",
                "lifecycle_lock_acquired_at": "",
                "lifecycle_lock_expires_at": "",
            }
        },
    )

    return result.modified_count > 0


async def delete_complaint_if_unchanged(
    complaint_id,
    user_id,
    expected_revision: int,
    expected_status: str,
) -> bool:
    """
    Atomically delete a complaint only when the caller's
    snapshot is still current.

    This prevents a stale deletion request from deleting a
    complaint that was edited, regenerated, or finalized
    after the deletion request first read it.
    """

    object_id = to_object_id(complaint_id)

    if object_id is None:
        return False

    normalized_expected_revision = normalize_revision(expected_revision)

    query: dict[str, Any] = {
        "_id": object_id,
        "user_id": user_id,
        "status": expected_status,
    }

    # Legacy complaints may not yet contain revision.
    if normalized_expected_revision == 0:
        query["$or"] = [
            {
                "revision": {
                    "$exists": False,
                }
            },
            {
                "revision": 0,
            },
        ]

    else:
        query["revision"] = normalized_expected_revision

    result = await complaints_collection.delete_one(query)

    return result.deleted_count > 0


async def delete_complaint(
    complaint_id,
    user_id,
) -> bool:
    object_id = to_object_id(complaint_id)

    if object_id is None:
        return False

    result = await complaints_collection.delete_one(
        {
            "_id": object_id,
            "user_id": user_id,
        }
    )

    return result.deleted_count > 0


async def get_finalized_complaint_citing_evidence(
    evidence_id,
    user_id,
) -> dict[str, Any] | None:
    """
    Return a finalized complaint owned by the user that
    cites the given evidence record.

    Evidence reference IDs are stored as strings inside
    complaint evidence_references.
    """

    evidence_id_string = str(evidence_id)

    return await complaints_collection.find_one(
        {
            "user_id": user_id,
            "status": "finalized",
            "evidence_references": {
                "$elemMatch": {
                    "evidence_id": evidence_id_string,
                }
            },
        }
    )
