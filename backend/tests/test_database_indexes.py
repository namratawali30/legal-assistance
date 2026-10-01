import uuid

import pytest

from bson import ObjectId

from pymongo.errors import (
    DuplicateKeyError,
)

from app.database import database

from app.db.collections import (
    CHAT_SESSIONS_COLLECTION,
    COMPLAINTS_COLLECTION,
    EVIDENCE_COLLECTION,
    MESSAGES_COLLECTION,
    USERS_COLLECTION,
)

from app.repositories.evidence_repository import (
    EVIDENCE_UNIQUE_SCOPE_INDEX,
)


async def get_index_information(
    collection_name: str,
):
    collection = database[collection_name]

    return await collection.index_information()


def find_index_by_key(
    index_information: dict,
    expected_key: list[tuple[str, int]],
) -> dict:
    for index_data in index_information.values():
        if index_data.get("key") == expected_key:
            return index_data

    raise AssertionError("Expected MongoDB index " f"was not found: {expected_key}")


# =========================================================
# USER INDEXES
# =========================================================


def test_user_email_index_is_unique(
    client,
):
    info = client.portal.call(
        get_index_information,
        USERS_COLLECTION,
    )

    index = find_index_by_key(
        info,
        [
            (
                "email",
                1,
            )
        ],
    )

    assert index.get("unique") is True


# =========================================================
# CHAT / MESSAGE INDEXES
# =========================================================


def test_chat_session_list_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        CHAT_SESSIONS_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ],
    )


def test_message_order_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        MESSAGES_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "session_id",
                1,
            ),
            (
                "created_at",
                1,
            ),
        ],
    )


# =========================================================
# COMPLAINT INDEXES
# =========================================================


def test_complaint_list_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        COMPLAINTS_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "user_id",
                1,
            ),
            (
                "updated_at",
                -1,
            ),
        ],
    )


def test_finalized_evidence_reference_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        COMPLAINTS_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "user_id",
                1,
            ),
            (
                "status",
                1,
            ),
            (
                "evidence_references.evidence_id",
                1,
            ),
        ],
    )


# =========================================================
# EVIDENCE INDEXES
# =========================================================


def test_evidence_unique_scope_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        EVIDENCE_COLLECTION,
    )

    assert EVIDENCE_UNIQUE_SCOPE_INDEX in info

    index = info[EVIDENCE_UNIQUE_SCOPE_INDEX]

    assert index["key"] == [
        (
            "user_id",
            1,
        ),
        (
            "complaint_id",
            1,
        ),
        (
            "sha256",
            1,
        ),
    ]

    assert index.get("unique") is True


def test_evidence_user_created_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        EVIDENCE_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "user_id",
                1,
            ),
            (
                "created_at",
                -1,
            ),
        ],
    )


def test_evidence_complaint_created_index_exists(
    client,
):
    info = client.portal.call(
        get_index_information,
        EVIDENCE_COLLECTION,
    )

    find_index_by_key(
        info,
        [
            (
                "user_id",
                1,
            ),
            (
                "complaint_id",
                1,
            ),
            (
                "created_at",
                -1,
            ),
        ],
    )


# =========================================================
# DATABASE-LEVEL UNIQUENESS
# =========================================================


def test_database_enforces_unique_user_email(
    client,
):
    email = "db-index-" f"{uuid.uuid4().hex}" "@example.com"

    async def exercise_constraint():
        collection = database[USERS_COLLECTION]

        try:
            await collection.insert_one(
                {
                    "email": email,
                }
            )

            with pytest.raises(DuplicateKeyError):
                await collection.insert_one(
                    {
                        "email": email,
                    }
                )

        finally:
            await collection.delete_many(
                {
                    "email": email,
                }
            )

    client.portal.call(exercise_constraint)


def test_database_enforces_unique_evidence_scope(
    client,
):
    user_id = ObjectId()

    sha256 = (uuid.uuid4().hex * 2)[:64]

    async def exercise_constraint():
        collection = database[EVIDENCE_COLLECTION]

        query = {
            "user_id": user_id,
            "complaint_id": None,
            "sha256": sha256,
        }

        try:
            await collection.insert_one(
                {
                    **query,
                    "status": "uploaded",
                }
            )

            with pytest.raises(DuplicateKeyError):
                await collection.insert_one(
                    {
                        **query,
                        "status": "uploaded",
                    }
                )

        finally:
            await collection.delete_many(query)

    client.portal.call(exercise_constraint)
