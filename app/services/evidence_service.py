import hmac
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pymongo.errors import DuplicateKeyError

from app.db.evidence_documents import (
    build_evidence_document,
)
from app.repositories.complaint_repository import (
    get_complaint,
)
from app.repositories.evidence_repository import (
    create_evidence,
    delete_evidence_metadata,
    find_duplicate_evidence,
    get_evidence,
    get_user_evidence,
    update_evidence,
)
from app.services.evidence_storage_service import (
    EvidenceStorageError,
    calculate_file_sha256,
    delete_stored_evidence_file,
    resolve_storage_path,
    save_evidence_upload,
)
from app.services.evidence_lifecycle_service import (
    ensure_evidence_not_finalized_locked,
)
from app.services.evidence_lifecycle_lock_service import (
    acquire_single_evidence_lock,
    release_single_evidence_lock,
)
from app.services.complaint_lifecycle_lock_service import (
    ComplaintLifecycleBusyError,
    ComplaintLifecycleReferenceError,
    acquire_complaint_lock,
    release_complaint_lock,
)


class EvidenceServiceError(Exception):
    """Base exception for evidence service operations."""


class EvidenceComplaintNotFoundError(EvidenceServiceError):
    """Raised when a linked complaint is missing or not owned."""


class EvidencePersistenceError(EvidenceServiceError):
    """Raised when evidence metadata cannot be persisted safely."""


class EvidenceDeleteError(EvidenceServiceError):
    """Raised when stored evidence cannot be safely deleted."""


class EvidenceFileUnavailableError(EvidenceServiceError):
    """Raised when evidence metadata exists but its file is unavailable."""


class EvidenceIntegrityError(EvidenceServiceError):
    """Raised when stored evidence no longer matches its recorded hash."""


class EvidenceDuplicateError(EvidenceServiceError):
    """Raised when the same evidence already exists in the same scope."""


class EvidenceComplaintBusyError(EvidenceServiceError):
    """
    Raised when linked evidence cannot safely be attached
    because another complaint lifecycle operation currently
    owns the complaint.
    """


ALLOWED_UPDATE_FIELDS = {
    "title",
    "description",
}


async def resolve_owned_complaint(
    complaint_id,
    user_id,
):
    if complaint_id is None:
        return None

    complaint = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not complaint:
        raise EvidenceComplaintNotFoundError("Complaint not found.")

    return complaint


def cleanup_newly_stored_file(
    storage_path: str,
    failure_message: str,
) -> None:
    try:
        delete_stored_evidence_file(storage_path)

    except Exception as exc:
        raise EvidencePersistenceError(failure_message) from exc


async def create_evidence_for_user(
    upload: UploadFile,
    user_id,
    complaint_id=None,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    # -------------------------------------------------
    # 1. VERIFY COMPLAINT OWNERSHIP FIRST
    # -------------------------------------------------

    linked_complaint = await resolve_owned_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    linked_complaint_id = linked_complaint["_id"] if linked_complaint else None

    # -------------------------------------------------
    # 2. VALIDATE + STORE PHYSICAL FILE
    # -------------------------------------------------
    #
    # SHA-256 becomes available only after the upload
    # has been streamed through the secure storage
    # service.

    stored_file = await save_evidence_upload(
        upload=upload,
        user_id=user_id,
    )

    # -------------------------------------------------
    # 3. DUPLICATE DETECTION
    # -------------------------------------------------

    try:
        duplicate = await find_duplicate_evidence(
            user_id=user_id,
            sha256=stored_file["sha256"],
            complaint_id=linked_complaint_id,
        )

    except DuplicateKeyError as exc:
        cleanup_newly_stored_file(
            storage_path=stored_file["storage_path"],
            failure_message=(
                "Duplicate evidence was detected, "
                "but the redundant stored copy "
                "could not be removed."
            ),
        )

        raise EvidenceDuplicateError(
            "This evidence file has already been " "uploaded to this location."
        ) from exc

    except Exception as exc:
        cleanup_newly_stored_file(
            storage_path=stored_file["storage_path"],
            failure_message=(
                "Evidence duplicate check failed and "
                "the temporary stored copy could not "
                "be cleaned up."
            ),
        )

        raise EvidencePersistenceError(
            "Evidence duplicate check could not " "be completed."
        ) from exc

    if duplicate:
        # The original database record and file stay.
        # Only the newly uploaded redundant copy is
        # removed.
        cleanup_newly_stored_file(
            storage_path=stored_file["storage_path"],
            failure_message=(
                "Duplicate evidence was detected, "
                "but the redundant stored copy "
                "could not be removed."
            ),
        )

        raise EvidenceDuplicateError(
            "This evidence file has already been " "uploaded to this location."
        )

    # -------------------------------------------------
    # 4. BUILD DATABASE DOCUMENT
    # -------------------------------------------------

    evidence_document = build_evidence_document(
        user_id=user_id,
        complaint_id=linked_complaint_id,
        title=title,
        description=description,
        original_filename=stored_file["original_filename"],
        stored_filename=stored_file["stored_filename"],
        storage_path=stored_file["storage_path"],
        evidence_type=stored_file["evidence_type"],
        media_type=stored_file["media_type"],
        file_extension=stored_file["file_extension"],
        size_bytes=stored_file["size_bytes"],
        sha256=stored_file["sha256"],
    )

    # -------------------------------------------------
    # 5. ACQUIRE LINKED-COMPLAINT LIFECYCLE LEASE
    # -------------------------------------------------
    #
    # Do this only after the potentially slow physical
    # upload has finished.
    #
    # The lease protects the short critical section where
    # the evidence record becomes linked to the complaint.

    complaint_lock_token = None

    if linked_complaint_id is not None:
        try:
            (
                complaint_lock_token,
                linked_complaint,
            ) = await acquire_complaint_lock(
                complaint_id=linked_complaint_id,
                user_id=user_id,
                operation="attach_evidence",
            )

        except ComplaintLifecycleReferenceError as exc:
            cleanup_newly_stored_file(
                storage_path=stored_file["storage_path"],
                failure_message=(
                    "The linked complaint disappeared "
                    "during evidence upload and the "
                    "stored file could not be cleaned up."
                ),
            )

            raise EvidenceComplaintNotFoundError("Complaint no longer exists.") from exc

        except ComplaintLifecycleBusyError as exc:
            cleanup_newly_stored_file(
                storage_path=stored_file["storage_path"],
                failure_message=(
                    "Evidence upload conflicted with "
                    "another complaint operation and "
                    "the stored file could not be "
                    "cleaned up."
                ),
            )

            raise EvidenceComplaintBusyError(
                "The complaint is currently being changed. "
                "Try uploading the evidence again shortly."
            ) from exc


    # -------------------------------------------------
    # 6. INSERT EVIDENCE WHILE COMPLAINT LEASE IS HELD
    # -------------------------------------------------

    try:
        try:
            evidence_id = await create_evidence(evidence_document)

        except DuplicateKeyError as exc:
            cleanup_newly_stored_file(
                storage_path=stored_file["storage_path"],
                failure_message=(
                    "Duplicate evidence was detected, "
                    "but the redundant stored copy "
                    "could not be removed."
                ),
            )

            raise EvidenceDuplicateError(
                "This evidence file has already been " "uploaded to this location."
            ) from exc

        except Exception as exc:
            cleanup_newly_stored_file(
                storage_path=stored_file["storage_path"],
                failure_message=(
                    "Evidence metadata could not be "
                    "saved and the stored file could "
                    "not be cleaned up."
                ),
            )

            raise EvidencePersistenceError(
                "Evidence metadata could not be saved."
            ) from exc

        # ---------------------------------------------
        # 7. FETCH CREATED RECORD
        # ---------------------------------------------

        try:
            evidence = await get_evidence(
                evidence_id=evidence_id,
                user_id=user_id,
            )

        except Exception as exc:
            # The INSERT already succeeded. Preserve the file
            # because MongoDB may already reference it.
            raise EvidencePersistenceError(
                "Evidence was stored but could not be "
                "retrieved after creation."
            ) from exc

        if not evidence:
            # The INSERT succeeded, so preserve the
            # physical artifact because MongoDB may
            # already reference it.
            raise EvidencePersistenceError(
                "Evidence was stored but could not be " "retrieved after creation."
            )

        return evidence

    finally:
        # Standalone evidence never acquires a complaint
        # lifecycle lease.
        if complaint_lock_token is not None and linked_complaint_id is not None:
            try:
                await release_complaint_lock(
                    complaint_id=(linked_complaint_id),
                    user_id=user_id,
                    lock_token=(complaint_lock_token),
                )

            except Exception:
                # Do not mask the upload result.
                #
                # The short-lived lease automatically
                # expires if release temporarily fails.
                pass


async def find_evidence(
    evidence_id,
    user_id,
) -> dict[str, Any] | None:
    return await get_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )


async def list_evidence_for_user(
    user_id,
    complaint_id=None,
) -> list[dict[str, Any]]:
    if complaint_id is not None:
        await resolve_owned_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
        )

    return await get_user_evidence(
        user_id=user_id,
        complaint_id=complaint_id,
    )


async def update_evidence_metadata(
    evidence_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    existing = await get_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )

    if not existing:
        return None

    cleaned_update: dict[str, Any] = {}

    for field_name, value in update_data.items():
        if field_name not in ALLOWED_UPDATE_FIELDS:
            continue

        cleaned_update[field_name] = value

    if not cleaned_update:
        return existing

    return await update_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
        update_data=cleaned_update,
    )


async def prepare_evidence_download(
    evidence_id,
    user_id,
) -> (
    tuple[
        dict[str, Any],
        Path,
    ]
    | None
):
    evidence = await get_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )

    if not evidence:
        return None

    storage_path = evidence.get("storage_path")

    if not storage_path:
        raise EvidenceFileUnavailableError("Stored evidence file is unavailable.")

    try:
        absolute_path = resolve_storage_path(storage_path)

    except EvidenceStorageError as exc:
        raise EvidenceFileUnavailableError(
            "Stored evidence file is unavailable."
        ) from exc

    if not absolute_path.exists() or not absolute_path.is_file():
        raise EvidenceFileUnavailableError("Stored evidence file is unavailable.")

    expected_size = evidence.get("size_bytes")
    try:
        actual_size = (absolute_path.stat().st_size)
    except OSError as exc:
        raise EvidenceFileUnavailableError(
            "Stored evidence file is unavailable."
        ) from exc
    if(
        expected_size is not None
        and actual_size != expected_size
    ):
        raise EvidenceIntegrityError(
            "Stored evidence failed its integrity check."
        )

    try:
        actual_hash = calculate_file_sha256(storage_path)

    except EvidenceStorageError as exc:
        raise EvidenceFileUnavailableError(
            "Stored evidence file is unavailable."
        ) from exc

    expected_hash = str(
        evidence.get(
            "sha256",
            "",
        )
    )

    if not expected_hash or not hmac.compare_digest(
        actual_hash.lower(),
        expected_hash.lower(),
    ):
        raise EvidenceIntegrityError("Stored evidence failed its integrity check.")

    return (
        evidence,
        absolute_path,
    )


async def remove_evidence(
    evidence_id,
    user_id,
) -> bool:
    # -------------------------------------------------
    # 1. VERIFY EVIDENCE EXISTS AND IS OWNED
    # -------------------------------------------------

    evidence = await find_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )

    if not evidence:
        return False

    lock_token = None

    try:
        # -------------------------------------------------
        # 2. ACQUIRE ATOMIC EVIDENCE LIFECYCLE LEASE
        # -------------------------------------------------
        #
        # Complaint finalization and destructive evidence
        # operations compete for this same lease.
        #
        # Once deletion owns the lease, finalization cannot
        # concurrently validate/finalize against this
        # evidence item.

        (
            lock_token,
            locked_evidence,
        ) = await acquire_single_evidence_lock(
            evidence_id=evidence["_id"],
            user_id=user_id,
            operation="delete_evidence",
        )

        # The initial ownership lookup happened before the
        # atomic lease acquisition. From this point onward,
        # use the document returned by the lock operation.
        evidence = locked_evidence

        # -------------------------------------------------
        # 3. RE-CHECK FINALIZED-COMPLAINT PROTECTION
        #    WHILE THE LIFECYCLE LEASE IS HELD
        # -------------------------------------------------
        #
        # This ordering is critical:
        #
        # lifecycle lease
        #     -> finalized complaint check
        #     -> physical deletion
        #     -> metadata deletion
        #
        # Running the finalized check before acquiring the
        # lifecycle lease would reintroduce a check-then-act
        # race.

        await ensure_evidence_not_finalized_locked(
            evidence_id=evidence["_id"],
            user_id=user_id,
        )

        # -------------------------------------------------
        # 4. DELETE PHYSICAL FILE FIRST
        # -------------------------------------------------
        #
        # Preserve the existing secure deletion behavior.
        # delete_stored_evidence_file() performs the storage
        # service's protected path resolution / deletion.

        storage_path = evidence.get("storage_path")

        if storage_path:
            try:
                delete_stored_evidence_file(storage_path)

            except EvidenceStorageError as exc:
                raise EvidenceDeleteError(
                    "Stored evidence file could not be deleted."
                ) from exc

        # -------------------------------------------------
        # 5. DELETE MONGODB METADATA SECOND
        # -------------------------------------------------

        try:
            deleted = await delete_evidence_metadata(
                evidence_id=evidence["_id"],
                user_id=user_id,
            )

        except Exception as exc:
            raise EvidencePersistenceError(
                "Evidence file was removed, but its "
                "database metadata could not be deleted."
            ) from exc

        if not deleted:
            raise EvidencePersistenceError(
                "Evidence file was removed, but its "
                "database metadata could not be deleted."
            )

        return True

    finally:
        # -------------------------------------------------
        # 6. ALWAYS RELEASE THE LIFECYCLE LEASE
        # -------------------------------------------------
        #
        # If MongoDB metadata was successfully deleted,
        # release becomes a harmless no-op because the
        # evidence document no longer exists.
        #
        # If deletion failed before metadata removal, this
        # releases the lease from the still-existing record.

        if lock_token is not None:
            try:
                await release_single_evidence_lock(
                    evidence_id=evidence["_id"],
                    user_id=user_id,
                    lock_token=lock_token,
                )

            except Exception:
                # Do not mask the original deletion result
                # or deletion exception if lock release
                # temporarily fails.
                #
                # The lifecycle lease has an expiry, which
                # provides recovery from stale locks.
                pass
