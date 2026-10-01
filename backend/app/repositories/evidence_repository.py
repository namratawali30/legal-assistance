from datetime import datetime, timezone, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import (
    ASCENDING,
    ReturnDocument,
    DESCENDING,
)

from app.database import database
from app.db.collections import (
    EVIDENCE_COLLECTION,
)

evidence_collection = database[EVIDENCE_COLLECTION]


EVIDENCE_UNIQUE_SCOPE_INDEX = "evidence_unique_user_scope_sha256"


async def ensure_evidence_indexes() -> None:
    # =====================================================
    # DUPLICATE-EVIDENCE INTEGRITY CONSTRAINT
    # =====================================================
    #
    # A user may not store the same SHA-256 twice in
    # the same complaint scope.
    #
    # complaint_id=None represents the user's general,
    # unlinked evidence scope.
    # =====================================================

    await evidence_collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "complaint_id",
                ASCENDING,
            ),
            (
                "sha256",
                ASCENDING,
            ),
        ],
        unique=True,
        name=EVIDENCE_UNIQUE_SCOPE_INDEX,
    )

    # =====================================================
    # ALL EVIDENCE FOR A USER
    # =====================================================
    #
    # Supports:
    #   find({"user_id": ...})
    #       .sort("created_at", -1)
    # =====================================================

    await evidence_collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=("evidence_user_created"),
    )

    # =====================================================
    # EVIDENCE FOR ONE COMPLAINT
    # =====================================================
    #
    # Supports:
    #   find({
    #       "user_id": ...,
    #       "complaint_id": ...
    #   }).sort("created_at", -1)
    #
    # The existing unique index also supports simple
    # complaint evidence counts through its prefix,
    # but it cannot satisfy the created_at sort.
    # =====================================================

    await evidence_collection.create_index(
        [
            (
                "user_id",
                ASCENDING,
            ),
            (
                "complaint_id",
                ASCENDING,
            ),
            (
                "created_at",
                DESCENDING,
            ),
        ],
        name=("evidence_user_complaint_created"),
    )


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


async def create_evidence(
    evidence_data: dict[str, Any],
):
    document = dict(evidence_data)

    result = await evidence_collection.insert_one(document)

    return result.inserted_id


async def get_evidence(
    evidence_id,
    user_id,
) -> dict[str, Any] | None:
    object_id = to_object_id(evidence_id)

    if object_id is None:
        return None

    return await evidence_collection.find_one(
        {
            "_id": object_id,
            "user_id": user_id,
        }
    )


async def get_user_evidence(
    user_id,
    complaint_id=None,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {
        "user_id": user_id,
    }

    if complaint_id is not None:
        complaint_object_id = to_object_id(complaint_id)

        if complaint_object_id is None:
            return []

        query["complaint_id"] = complaint_object_id

    cursor = evidence_collection.find(query).sort(
        "created_at",
        -1,
    )

    return await cursor.to_list(length=500)


async def iter_evidence_records_for_reconciliation(
    user_id=None,
    batch_size: int = 250,
):
    """
    Stream the minimal evidence metadata required by the
    reconciliation service without materializing the entire
    evidence collection in memory.
    """

    query: dict[str, Any] = {}

    if user_id is not None:
        query["user_id"] = user_id

    projection = {
        "_id": 1,
        "user_id": 1,
        "complaint_id": 1,
        "original_filename": 1,
        "storage_path": 1,
        "size_bytes": 1,
        "sha256": 1,
    }

    cursor = (
        evidence_collection.find(
            query,
            projection,
        )
        .sort(
            "_id",
            ASCENDING,
        )
        .batch_size(batch_size)
    )

    async for evidence in cursor:
        yield evidence


async def count_evidence_for_complaint(
    complaint_id,
    user_id,
) -> int:
    complaint_object_id = to_object_id(complaint_id)

    if complaint_object_id is None:
        return 0

    return await evidence_collection.count_documents(
        {
            "user_id": user_id,
            "complaint_id": complaint_object_id,
        }
    )


async def find_duplicate_evidence(
    user_id,
    sha256: str,
    complaint_id=None,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "user_id": user_id,
        "sha256": sha256,
        "status": "uploaded",
    }

    if complaint_id is None:
        query["complaint_id"] = None

    else:
        complaint_object_id = to_object_id(complaint_id)

        if complaint_object_id is None:
            return None

        query["complaint_id"] = complaint_object_id

    return await evidence_collection.find_one(query)


async def claim_evidence_for_processing(
    evidence_id,
    user_id,
    allowed_statuses: list[str],
) -> dict[str, Any] | None:
    object_id = to_object_id(evidence_id)

    if object_id is None:
        return None

    status_conditions: list[dict[str, Any]] = [
        {"processing_status": {"$in": allowed_statuses}}
    ]

    # Compatibility with any older evidence records
    # created before processing_status was introduced.
    if "pending" in allowed_statuses:
        status_conditions.append({"processing_status": {"$exists": False}})

    now = datetime.now(timezone.utc)

    return await evidence_collection.find_one_and_update(
        {
            "_id": object_id,
            "user_id": user_id,
            "$or": status_conditions,
        },
        {
            "$set": {
                "processing_status": "processing",
                # Clear previous extraction state when
                # claiming/retrying processing.
                "extraction_method": None,
                "extracted_text": None,
                "extracted_character_count": 0,
                "extracted_page_count": None,
                "processed_at": None,
                "processing_error": None,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )


async def update_evidence(
    evidence_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    object_id = to_object_id(evidence_id)

    if object_id is None:
        return None

    safe_update = dict(update_data)

    for field_name in (
        "_id",
        "user_id",
        "complaint_id",
        "created_at",
        "original_filename",
        "stored_filename",
        "storage_path",
        "evidence_type",
        "media_type",
        "file_extension",
        "size_bytes",
        "sha256",
    ):
        safe_update.pop(
            field_name,
            None,
        )

    safe_update["updated_at"] = datetime.now(timezone.utc)

    result = await evidence_collection.update_one(
        {
            "_id": object_id,
            "user_id": user_id,
        },
        {
            "$set": safe_update,
        },
    )

    if result.matched_count == 0:
        return None

    return await get_evidence(
        evidence_id=object_id,
        user_id=user_id,
    )


async def delete_evidence_metadata(
    evidence_id,
    user_id,
) -> bool:
    object_id = to_object_id(evidence_id)

    if object_id is None:
        return False

    result = await evidence_collection.delete_one(
        {
            "_id": object_id,
            "user_id": user_id,
        }
    )

    return result.deleted_count > 0


async def acquire_evidence_lifecycle_lock(
    evidence_id,
    user_id,
    lock_token: str,
    operation: str,
    lease_seconds: int = 300,
) -> dict[str, Any] | None:
    """
    Atomically acquire a short-lived lifecycle lock.

    The lock coordinates complaint finalization with
    destructive/mutating evidence operations.

    A lock may be acquired when:
    - no lifecycle lock exists, or
    - the previous lock lease has expired.

    Returns the locked evidence document on success.
    Returns None when another active operation owns it.
    """

    object_id = to_object_id(evidence_id)

    if object_id is None:
        return None

    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(seconds=lease_seconds)

    return await evidence_collection.find_one_and_update(
        {
            "_id": object_id,
            "user_id": user_id,
            "$or": [
                {"lifecycle_lock_token": {"$exists": False}},
                {"lifecycle_lock_token": None},
                {"lifecycle_lock_expires_at": {"$lte": now}},
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


async def release_evidence_lifecycle_lock(
    evidence_id,
    user_id,
    lock_token: str,
) -> bool:
    """
    Release a lifecycle lock only when the caller still
    owns that exact lock token.

    This prevents one request from accidentally releasing
    another request's newer lock.
    """

    object_id = to_object_id(evidence_id)

    if object_id is None:
        return False

    result = await evidence_collection.update_one(
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
