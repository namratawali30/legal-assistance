import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from app.repositories.evidence_repository import (
    acquire_evidence_lifecycle_lock,
    evidence_collection,
    release_evidence_lifecycle_lock,
)
from app.services.evidence_lifecycle_lock_service import (
    EvidenceLifecycleBusyError,
    acquire_multiple_evidence_locks,
    release_multiple_evidence_locks,
)


async def create_test_evidence(
    user_id,
):
    now = datetime.now(timezone.utc)

    result = await evidence_collection.insert_one(
        {
            "user_id": user_id,
            "complaint_id": None,
            "title": "Lifecycle lock test",
            "original_filename": (f"{uuid.uuid4().hex}.txt"),
            "evidence_type": "text",
            "media_type": "text/plain",
            "file_extension": ".txt",
            "size_bytes": 4,
            "sha256": uuid.uuid4().hex,
            "status": "uploaded",
            "processing_status": "ready",
            "extracted_text": "test",
            "created_at": now,
            "updated_at": now,
        }
    )

    return result.inserted_id


def test_only_one_active_lifecycle_lock_can_exist(
    client,
):
    async def run():
        from bson import ObjectId

        user_id = ObjectId()

        evidence_id = await create_test_evidence(user_id)

        first_token = uuid.uuid4().hex
        second_token = uuid.uuid4().hex

        first = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=first_token,
            operation="first",
        )

        assert first is not None

        second = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=second_token,
            operation="second",
        )

        assert second is None

        released = await release_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=first_token,
        )

        assert released is True

        third = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=second_token,
            operation="second",
        )

        assert third is not None

    client.portal.call(run)


def test_wrong_token_cannot_release_lock(
    client,
):
    async def run():
        from bson import ObjectId

        user_id = ObjectId()

        evidence_id = await create_test_evidence(user_id)

        real_token = uuid.uuid4().hex

        locked = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=real_token,
            operation="test",
        )

        assert locked

        released = await release_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token="wrong-token",
        )

        assert released is False

        still_locked = await evidence_collection.find_one({"_id": evidence_id})

        assert still_locked["lifecycle_lock_token"] == real_token

    client.portal.call(run)


def test_expired_lifecycle_lock_can_be_reclaimed(
    client,
):
    async def run():
        from bson import ObjectId

        user_id = ObjectId()

        evidence_id = await create_test_evidence(user_id)

        await evidence_collection.update_one(
            {"_id": evidence_id},
            {
                "$set": {
                    "lifecycle_lock_token": "expired-token",
                    "lifecycle_lock_operation": "old-operation",
                    "lifecycle_lock_expires_at": (
                        datetime.now(timezone.utc) - timedelta(minutes=1)
                    ),
                }
            },
        )

        new_token = uuid.uuid4().hex

        locked = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=new_token,
            operation="new-operation",
        )

        assert locked is not None

        assert locked["lifecycle_lock_token"] == new_token

    client.portal.call(run)


def test_multiple_lock_acquisition_rolls_back_on_conflict(
    client,
):
    async def run():
        from bson import ObjectId

        user_id = ObjectId()

        evidence_a = await create_test_evidence(user_id)

        evidence_b = await create_test_evidence(user_id)

        blocker_token = uuid.uuid4().hex

        blocker = await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_b,
            user_id=user_id,
            lock_token=blocker_token,
            operation="blocker",
        )

        assert blocker

        with pytest.raises(EvidenceLifecycleBusyError):
            await acquire_multiple_evidence_locks(
                evidence_ids=[
                    evidence_a,
                    evidence_b,
                ],
                user_id=user_id,
                operation="finalize",
            )

        evidence_a_after = await evidence_collection.find_one({"_id": evidence_a})

        # The successfully acquired first lock must
        # have been rolled back.
        assert evidence_a_after.get("lifecycle_lock_token") is None

        evidence_b_after = await evidence_collection.find_one({"_id": evidence_b})

        # The unrelated blocker remains untouched.
        assert evidence_b_after["lifecycle_lock_token"] == blocker_token

    client.portal.call(run)


def test_multiple_locks_can_be_released(
    client,
):
    async def run():
        from bson import ObjectId

        user_id = ObjectId()

        evidence_a = await create_test_evidence(user_id)

        evidence_b = await create_test_evidence(user_id)

        token, locked = await acquire_multiple_evidence_locks(
            evidence_ids=[
                evidence_a,
                evidence_b,
            ],
            user_id=user_id,
            operation="finalize",
        )

        assert len(locked) == 2

        await release_multiple_evidence_locks(
            evidence_ids=[
                evidence_a,
                evidence_b,
            ],
            user_id=user_id,
            lock_token=token,
        )

        first = await evidence_collection.find_one({"_id": evidence_a})

        second = await evidence_collection.find_one({"_id": evidence_b})

        assert first.get("lifecycle_lock_token") is None

        assert second.get("lifecycle_lock_token") is None

    client.portal.call(run)
