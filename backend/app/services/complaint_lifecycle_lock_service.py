import uuid

from app.repositories.complaint_repository import (
    acquire_complaint_lifecycle_lock,
    get_complaint,
    release_complaint_lifecycle_lock,
)

DEFAULT_COMPLAINT_LIFECYCLE_LEASE_SECONDS = 300


class ComplaintLifecycleLockError(Exception):
    """Base complaint lifecycle lease error."""


class ComplaintLifecycleBusyError(ComplaintLifecycleLockError):
    """Another operation currently owns the complaint lease."""


class ComplaintLifecycleReferenceError(ComplaintLifecycleLockError):
    """The complaint no longer exists or is not owned."""


async def acquire_complaint_lock(
    complaint_id,
    user_id,
    operation: str,
    lease_seconds: int = (DEFAULT_COMPLAINT_LIFECYCLE_LEASE_SECONDS),
) -> tuple[
    str,
    dict,
]:
    """
    Acquire a short-lived lifecycle lease for one
    complaint.

    Returns:
        (lock_token, locked_complaint)
    """

    lock_token = uuid.uuid4().hex

    locked = await acquire_complaint_lifecycle_lock(
        complaint_id=complaint_id,
        user_id=user_id,
        lock_token=lock_token,
        operation=operation,
        lease_seconds=lease_seconds,
    )

    if locked:
        return (
            lock_token,
            locked,
        )

    # Distinguish an active competing lease from a
    # complaint that disappeared.
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if existing:
        raise ComplaintLifecycleBusyError("The complaint is currently being changed.")

    raise ComplaintLifecycleReferenceError("The complaint is no longer available.")


async def release_complaint_lock(
    complaint_id,
    user_id,
    lock_token: str,
) -> bool:
    return await release_complaint_lifecycle_lock(
        complaint_id=complaint_id,
        user_id=user_id,
        lock_token=lock_token,
    )
