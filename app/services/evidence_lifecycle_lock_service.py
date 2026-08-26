import uuid
from typing import Any

from app.repositories.evidence_repository import (
    acquire_evidence_lifecycle_lock,
    get_evidence,
    release_evidence_lifecycle_lock,
    to_object_id,
)

DEFAULT_LIFECYCLE_LEASE_SECONDS = 300


class EvidenceLifecycleLockError(Exception):
    """
    Base lifecycle-lock error.
    """


class EvidenceLifecycleBusyError(EvidenceLifecycleLockError):
    """
    Raised when another operation currently owns an
    evidence lifecycle lease.
    """


class EvidenceLifecycleReferenceError(EvidenceLifecycleLockError):
    """
    Raised when an evidence reference cannot be converted
    into a valid evidence identifier.
    """


async def acquire_single_evidence_lock(
    evidence_id,
    user_id,
    operation: str,
    lease_seconds: int = (DEFAULT_LIFECYCLE_LEASE_SECONDS),
) -> tuple[str, Any]:
    """
    Acquire one evidence lifecycle lock.

    Returns:
        (lock_token, locked_evidence_document)
    """

    object_id = to_object_id(evidence_id)

    if object_id is None:
        raise EvidenceLifecycleReferenceError("Invalid evidence identifier.")

    lock_token = uuid.uuid4().hex

    locked = await acquire_evidence_lifecycle_lock(
        evidence_id=object_id,
        user_id=user_id,
        lock_token=lock_token,
        operation=operation,
        lease_seconds=lease_seconds,
    )

    if not locked:
        raise EvidenceLifecycleBusyError(
            "The evidence is currently being changed "
            "by another operation. Try again shortly."
        )

    return (
        lock_token,
        locked,
    )


async def release_single_evidence_lock(
    evidence_id,
    user_id,
    lock_token: str,
) -> None:
    """
    Best-effort release of one owned lifecycle lock.
    """

    await release_evidence_lifecycle_lock(
        evidence_id=evidence_id,
        user_id=user_id,
        lock_token=lock_token,
    )


async def acquire_multiple_evidence_locks(
    evidence_ids: list,
    user_id,
    operation: str,
    lease_seconds: int = (DEFAULT_LIFECYCLE_LEASE_SECONDS),
) -> tuple[
    str,
    list[Any],
]:
    """
    Acquire lifecycle locks for multiple evidence items.

    All items use one shared token.

    Evidence IDs are sorted deterministically to avoid
    lock-order deadlocks when two finalizations overlap.

    If any acquisition fails, every previously acquired
    lock is released before the error is re-raised.
    """

    normalized_ids = []

    seen = set()

    for evidence_id in evidence_ids:
        object_id = to_object_id(evidence_id)

        if object_id is None:
            raise EvidenceLifecycleReferenceError("Invalid evidence identifier.")

        object_id_string = str(object_id)

        if object_id_string in seen:
            continue

        seen.add(object_id_string)

        normalized_ids.append(object_id)

    normalized_ids.sort(key=str)

    if not normalized_ids:
        return (
            uuid.uuid4().hex,
            [],
        )

    lock_token = uuid.uuid4().hex

    acquired_ids = []

    locked_documents = []

    try:
        for evidence_id in normalized_ids:
            locked = await acquire_evidence_lifecycle_lock(
                evidence_id=evidence_id,
                user_id=user_id,
                lock_token=lock_token,
                operation=operation,
                lease_seconds=(lease_seconds),
            )

            if not locked:
                current = await get_evidence(
                    evidence_id=evidence_id,
                    user_id=user_id,
                )
                if not current:
                    raise EvidenceLifecycleReferenceError(
                        "One or more evidence items are "
                        "no longer available."
                )
                raise EvidenceLifecycleBusyError(
                    "One or more evidence items are "
                    "currently being changed by another "
                    "operation. Try again later."

                )

            acquired_ids.append(evidence_id)

            locked_documents.append(locked)

        return (
            lock_token,
            locked_documents,
        )

    except Exception:
        for evidence_id in acquired_ids:
            try:
                await release_evidence_lifecycle_lock(
                    evidence_id=evidence_id,
                    user_id=user_id,
                    lock_token=lock_token,
                )

            except Exception:
                # Best-effort rollback.
                #
                # The lease expiry remains a safety net
                # if MongoDB becomes unavailable while
                # rollback is occurring.
                pass

        raise


async def release_multiple_evidence_locks(
    evidence_ids: list,
    user_id,
    lock_token: str,
) -> None:
    """
    Best-effort release for a group of locks owned by the
    same operation token.
    """

    seen = set()

    for evidence_id in evidence_ids:
        object_id = to_object_id(evidence_id)

        if object_id is None:
            continue

        object_id_string = str(object_id)

        if object_id_string in seen:
            continue

        seen.add(object_id_string)

        try:
            await release_evidence_lifecycle_lock(
                evidence_id=object_id,
                user_id=user_id,
                lock_token=lock_token,
            )

        except Exception:
            # Do not hide the original operation failure.
            # The lease automatically expires.
            pass
