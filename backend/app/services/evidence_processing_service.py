import asyncio
from datetime import datetime, timezone
from typing import Any

from app.repositories.evidence_repository import (
    claim_evidence_for_processing,
    get_evidence,
    update_evidence,
)
from app.services.evidence_lifecycle_service import (
    ensure_evidence_not_finalized_locked,
)
from app.services.evidence_text_extraction_service import (
    EvidenceExtractionError,
    extract_evidence_text,
)
from app.services.evidence_lifecycle_lock_service import (
    acquire_single_evidence_lock,
    release_single_evidence_lock,
)

# =========================================================
# PROCESSING STATES
# =========================================================

PROCESSING_STATUS_PENDING = "pending"
PROCESSING_STATUS_PROCESSING = "processing"
PROCESSING_STATUS_READY = "ready"
PROCESSING_STATUS_NO_TEXT = "no_text"
PROCESSING_STATUS_REQUIRES_OCR = "requires_ocr"
PROCESSING_STATUS_FAILED = "failed"


PROCESSED_STATES = {
    PROCESSING_STATUS_READY,
    PROCESSING_STATUS_NO_TEXT,
    PROCESSING_STATUS_REQUIRES_OCR,
    PROCESSING_STATUS_FAILED,
}


# =========================================================
# EXCEPTIONS
# =========================================================


class EvidenceProcessingError(Exception):
    """
    Base exception for evidence-processing failures.
    """


class EvidenceProcessingConflictError(EvidenceProcessingError):
    """
    Raised when evidence cannot enter processing because
    its current state conflicts with the requested action.
    """


class EvidenceProcessingPersistenceError(EvidenceProcessingError):
    """
    Raised when the processing result cannot be
    persisted safely.
    """


class EvidenceProcessingInProgressError(EvidenceProcessingConflictError):
    """
    Raised when another processing operation already owns
    the evidence record.
    """


class EvidenceAlreadyProcessedError(EvidenceProcessingConflictError):
    """
    Raised when evidence has already been processed and
    retry=True was not supplied.
    """


# =========================================================
# HELPERS
# =========================================================


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_processing_error(
    exc: Exception,
) -> str:
    """
    Persist only a safe public-facing failure message.

    Detailed parser/filesystem/provider exception text must
    not be stored in a field returned by the public API.
    Detailed diagnostics belong in internal logging.
    """

    return "Evidence processing failed."


def get_extraction_status(
    extraction_result: dict[str, Any],
) -> str:
    """
    Support the extraction service result contract while
    failing closed for unexpected statuses.
    """

    extraction_status = extraction_result.get(
        "processing_status"
    ) or extraction_result.get("status")

    allowed_statuses = {
        PROCESSING_STATUS_READY,
        PROCESSING_STATUS_NO_TEXT,
        PROCESSING_STATUS_REQUIRES_OCR,
    }

    if extraction_status not in allowed_statuses:
        raise EvidenceProcessingError(
            "Evidence extraction returned an " "unsupported processing status."
        )

    return extraction_status


def get_extracted_text(
    extraction_result: dict[str, Any],
) -> str | None:
    """
    Return extracted text without exposing it through the
    public API. The value remains private Mongo metadata.
    """

    value = extraction_result.get("extracted_text")

    if value is None:
        value = extraction_result.get("text")

    if value is None:
        return None

    value = str(value)

    if not value:
        return None

    return value


def build_success_update(
    extraction_result: dict[str, Any],
) -> dict[str, Any]:
    processing_status = get_extraction_status(extraction_result)

    extracted_text = get_extracted_text(extraction_result)

    if processing_status == PROCESSING_STATUS_READY and not extracted_text:
        raise EvidenceProcessingError(
            "Evidence extraction reported ready " "without extracted text."
        )

    if processing_status != PROCESSING_STATUS_READY:
        extracted_text = None

    # Extraction service result -> persisted DB field.
    #
    # Support both names so we remain compatible with
    # existing extraction-service results.
    extraction_method = extraction_result.get(
        "extraction_method"
    ) or extraction_result.get("method")

    extracted_character_count = extraction_result.get("extracted_character_count")

    if extracted_character_count is None:
        extracted_character_count = extraction_result.get("character_count")

    if extracted_character_count is None:
        extracted_character_count = len(extracted_text) if extracted_text else 0

    extracted_page_count = extraction_result.get("extracted_page_count")

    if extracted_page_count is None:
        extracted_page_count = extraction_result.get("page_count")

    return {
        "processing_status": processing_status,
        "extracted_text": extracted_text,
        "extraction_method": extraction_method,
        "extracted_character_count": extracted_character_count,
        "extracted_page_count": extracted_page_count,
        "processed_at": utc_now(),
        "processing_error": None,
    }


def build_failed_update(
    exc: Exception,
) -> dict[str, Any]:
    return {
        "processing_status": PROCESSING_STATUS_FAILED,
        # Never leave stale text from an older successful
        # processing run after a failed retry.
        "extracted_text": None,
        "extraction_method": None,
        "extracted_character_count": 0,
        "extracted_page_count": None,
        "processed_at": utc_now(),
        "processing_error": safe_processing_error(exc),
    }


# =========================================================
# PROCESS EVIDENCE
# =========================================================


async def process_evidence_for_user(
    evidence_id,
    user_id,
    retry: bool = False,
) -> dict[str, Any] | None:
    """
    Process evidence while holding its lifecycle lease.

    The lifecycle lease prevents complaint finalization
    from racing with evidence reprocessing.
    """

    existing = await get_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )

    if not existing:
        return None

    lock_token = None

    try:
        # -------------------------------------------------
        # 1. ACQUIRE MUTATION LEASE
        # -------------------------------------------------

        (
            lock_token,
            locked_evidence,
        ) = await acquire_single_evidence_lock(
            evidence_id=existing["_id"],
            user_id=user_id,
            operation="reprocess_evidence",
        )

        # Work from the document returned by the atomic
        # lock acquisition rather than the earlier stale
        # read.
        existing = locked_evidence

        # -------------------------------------------------
        # 2. RE-CHECK FINALIZED PROTECTION WHILE LOCKED
        # -------------------------------------------------

        await ensure_evidence_not_finalized_locked(
            evidence_id=existing["_id"],
            user_id=user_id,
        )

        # -------------------------------------------------
        # 3. PROCESSING STATE
        # -------------------------------------------------

        current_status = existing.get(
            "processing_status",
            PROCESSING_STATUS_PENDING,
        )

        if not current_status:
            current_status = PROCESSING_STATUS_PENDING

        if (
            current_status
            == PROCESSING_STATUS_PROCESSING
            and not retry
    ):
            raise EvidenceProcessingInProgressError(
                "Evidence is already being processed."
            )

        if current_status in PROCESSED_STATES and not retry:
            raise EvidenceAlreadyProcessedError(
                "Evidence has already been processed. "
                "Set retry=true to process it again."
            )

        if retry:
            allowed_statuses = [
                PROCESSING_STATUS_PENDING,
                PROCESSING_STATUS_PROCESSING,
                PROCESSING_STATUS_READY,
                PROCESSING_STATUS_NO_TEXT,
                PROCESSING_STATUS_REQUIRES_OCR,
                PROCESSING_STATUS_FAILED,
            ]

        else:
            allowed_statuses = [
                PROCESSING_STATUS_PENDING,
            ]

        # -------------------------------------------------
        # 4. ATOMIC PROCESSING CLAIM
        # -------------------------------------------------

        claimed = await claim_evidence_for_processing(
            evidence_id=existing["_id"],
            user_id=user_id,
            allowed_statuses=allowed_statuses,
        )

        if not claimed:
            latest = await get_evidence(
                evidence_id=existing["_id"],
                user_id=user_id,
            )

            if not latest:
                return None

            latest_status = latest.get(
                "processing_status",
                PROCESSING_STATUS_PENDING,
            )

            if latest_status == PROCESSING_STATUS_PROCESSING:
                raise EvidenceProcessingInProgressError(
                    "Evidence is already being processed."
                )

            raise EvidenceProcessingConflictError(
                "Evidence processing state changed " "before processing could begin."
            )

        # -------------------------------------------------
        # 5. EXTRACTION
        # -------------------------------------------------

        try:
            extraction_result = await asyncio.to_thread(
                extract_evidence_text,
                claimed,
            )

            if not isinstance(
                extraction_result,
                dict,
            ):
                raise EvidenceProcessingError(
                    "Evidence extraction returned " "an invalid result."
                )

            update_data = build_success_update(extraction_result)

        except EvidenceExtractionError as exc:
            update_data = build_failed_update(exc)

        except EvidenceProcessingError as exc:
            update_data = build_failed_update(exc)

        except Exception as exc:
            update_data = build_failed_update(exc)

                # -------------------------------------------------
        # 6. PERSIST RESULT
        # -------------------------------------------------

        try:
            updated = await update_evidence(
                evidence_id=claimed["_id"],
                user_id=user_id,
                update_data=update_data,
            )

        except Exception as exc:
            raise EvidenceProcessingPersistenceError(
                "Evidence processing completed, "
                "but the processing result could "
                "not be persisted."
            ) from exc

        if not updated:
            raise EvidenceProcessingPersistenceError(
                "Evidence processing completed, "
                "but the processing result could "
                "not be persisted."
            )

        return updated

    finally:
        # -------------------------------------------------
        # 7. ALWAYS RELEASE LEASE
        # -------------------------------------------------

        if lock_token is not None:
            try:
                await release_single_evidence_lock(
                    evidence_id=existing["_id"],
                    user_id=user_id,
                    lock_token=lock_token,
                )

            except Exception:
                # Do not mask the processing result or
                # the original processing exception.
                #
                # The lifecycle lease expires
                # automatically.
                pass