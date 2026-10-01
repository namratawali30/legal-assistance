from datetime import date, datetime, timezone
from typing import Any

from app.db.complaint_documents import (
    build_complaint_document,
)
from app.rag.citation_guard import (
    extract_citations,
    validate_citations,
)
from app.rag.evidence_citation_guard import (
    extract_evidence_citations,
    validate_evidence_citations,
)
from app.repositories.complaint_repository import (
    create_complaint,
    delete_complaint,
    delete_complaint_if_unchanged,
    get_complaint,
    get_user_complaints,
    update_complaint,
    update_complaint_if_unchanged,
)
from app.repositories.evidence_repository import (
    count_evidence_for_complaint,
)
from app.services.evidence_consistency_service import (
    validate_complaint_evidence_consistency,
)
from app.services.evidence_lifecycle_lock_service import (
    EvidenceLifecycleBusyError,
    EvidenceLifecycleReferenceError,
    acquire_multiple_evidence_locks,
    release_multiple_evidence_locks,
)
from app.services.complaint_lifecycle_lock_service import (
    ComplaintLifecycleBusyError,
    ComplaintLifecycleReferenceError,
    acquire_complaint_lock,
    release_complaint_lock,
)
from app.services.complaint_lifecycle_lock_service import (
    ComplaintLifecycleBusyError,
    ComplaintLifecycleReferenceError,
    acquire_complaint_lock,
    release_complaint_lock,
)

IMMUTABLE_FIELDS = {
    "_id",
    "user_id",
    "created_at",
    "generated_at",
    "finalized_at",
    "generated_text",
    "sources",
    "evidence_references",
    "status",
}


class ComplaintStateError(Exception):
    """Base exception for invalid complaint state operations."""


class ComplaintFinalizedError(ComplaintStateError):
    """Raised when attempting to modify a finalized complaint."""


class ComplaintNotGeneratedError(ComplaintStateError):
    """Raised when generated text does not yet exist."""


class ComplaintFinalizationError(ComplaintStateError):
    """Raised when a complaint cannot safely be finalized."""


class ComplaintConcurrentUpdateError(ComplaintFinalizationError):
    """
    Raised when a complaint changes between the initial
    read and the attempted atomic write.

    It subclasses ComplaintFinalizationError so existing
    API 409 handling remains compatible.
    """


class ComplaintHasEvidenceError(ComplaintStateError):
    """Raised when evidence is still linked to a complaint."""

class ComplaintPersistenceError(ComplaintStateError):
    """
    Raised when a complaint persistence operation
    fails or its outcome cannot be confirmed safely.
    """


def serialize_update_value(
    field_name: str,
    value,
):
    if field_name == "incident_date":
        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):
            return value.date().isoformat()

        if isinstance(
            value,
            date,
        ):
            return value.isoformat()

    return value


def get_allowed_legal_citations(
    complaint: dict[str, Any],
) -> list[str]:
    return [
        source.get("citation_id")
        for source in complaint.get(
            "sources",
            [],
        )
        if source.get("citation_id")
    ]


def get_allowed_evidence_citations(
    complaint: dict[str, Any],
) -> list[str]:
    return [
        reference.get("citation_id")
        for reference in complaint.get(
            "evidence_references",
            [],
        )
        if reference.get("citation_id")
    ]


def validate_saved_complaint_citations(
    generated_text: str,
    complaint: dict[str, Any],
    require_legal_citation: bool,
) -> dict[str, Any]:
    """
    Validate the two independent citation namespaces.

    SOURCE_n:
        authoritative legal source

    EVIDENCE_n:
        user-supplied factual evidence
    """

    allowed_legal_citations = get_allowed_legal_citations(complaint)

    allowed_evidence_citations = get_allowed_evidence_citations(complaint)

    legal_validation = validate_citations(
        answer=generated_text,
        allowed_citations=allowed_legal_citations,
    )

    evidence_validation = validate_evidence_citations(
        answer=generated_text,
        allowed_citations=allowed_evidence_citations,
    )

    used_legal_citations = extract_citations(generated_text)

    used_evidence_citations = extract_evidence_citations(generated_text)

    valid = legal_validation["valid"] and evidence_validation["valid"]

    if require_legal_citation and not used_legal_citations:
        valid = False

    return {
        "valid": valid,
        "legal_validation": legal_validation,
        "evidence_validation": evidence_validation,
        "used_legal_citations": used_legal_citations,
        "used_evidence_citations": used_evidence_citations,
        "allowed_legal_citations": allowed_legal_citations,
        "allowed_evidence_citations": allowed_evidence_citations,
    }


def get_used_evidence_references(
    complaint: dict[str, Any],
    used_evidence_citations: list[str],
) -> list[dict[str, Any]]:
    """
    Return only evidence snapshot references that are
    actually cited by the complaint text being finalized.

    This canonicalizes evidence_references at finalization
    so stale or unused evidence snapshots are not retained.

    If the final complaint contains no evidence citations,
    an empty list is returned.
    """

    used_citations = {
        str(citation).strip().upper()
        for citation in used_evidence_citations
        if citation and str(citation).strip()
    }

    if not used_citations:
        return []

    stored_references = complaint.get(
        "evidence_references",
        [],
    )

    if not isinstance(
        stored_references,
        list,
    ):
        return []

    canonical_references: list[dict[str, Any]] = []

    for reference in stored_references:
        if not isinstance(
            reference,
            dict,
        ):
            continue

        citation_id = (
            str(
                reference.get(
                    "citation_id",
                    "",
                )
            )
            .strip()
            .upper()
        )

        if not citation_id:
            continue

        if citation_id not in used_citations:
            continue

        canonical_references.append(reference)

    return canonical_references


def get_complaint_revision(
    complaint: dict[str, Any],
) -> int:
    try:
        revision = int(
            complaint.get(
                "revision",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0

    return max(
        revision,
        0,
    )


async def create_complaint_draft(
    user_id,
    complaint_data: dict[str, Any],
) -> dict[str, Any] | None:
    category = complaint_data["category"]

    if hasattr(
        category,
        "value",
    ):
        category = category.value

    document = build_complaint_document(
        user_id=user_id,
        title=complaint_data["title"],
        category=category,
        complainant_name=complaint_data["complainant_name"],
        complainant_address=complaint_data.get("complainant_address"),
        complainant_contact=complaint_data.get("complainant_contact"),
        respondent_name=complaint_data["respondent_name"],
        respondent_address=complaint_data.get("respondent_address"),
        incident_date=complaint_data.get("incident_date"),
        incident_location=complaint_data.get("incident_location"),
        facts=complaint_data["facts"],
        relief_requested=complaint_data.get("relief_requested"),
        additional_details=complaint_data.get("additional_details"),
    )

    complaint_id = await create_complaint(document)

    return await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )


async def find_complaint(
    complaint_id,
    user_id,
) -> dict[str, Any] | None:
    return await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )


async def list_user_complaints(
    user_id,
) -> list[dict[str, Any]]:
    return await get_user_complaints(user_id=user_id)


async def update_complaint_draft(
    complaint_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )

    if current_status == "finalized":
        raise ComplaintFinalizedError("Finalized complaints cannot be edited.")

    expected_revision = get_complaint_revision(existing)

    cleaned_update = {}

    for field_name, value in update_data.items():
        if field_name in IMMUTABLE_FIELDS:
            continue

        if field_name == "category" and hasattr(
            value,
            "value",
        ):
            value = value.value

        cleaned_update[field_name] = serialize_update_value(
            field_name,
            value,
        )

    if not cleaned_update:
        return existing

    if current_status in {
        "generated",
        "edited",
    }:
        cleaned_update["status"] = "edited"

    updated = await update_complaint_if_unchanged(
        complaint_id=complaint_id,
        user_id=user_id,
        expected_revision=(expected_revision),
        expected_status=(current_status),
        update_data=(cleaned_update),
    )

    if updated:
        return updated

    latest = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not latest:
        return None

    if (
        latest.get(
            "status",
            "draft",
        )
        == "finalized"
    ):
        raise ComplaintFinalizedError(
            "The complaint was finalized while " "the edit was in progress."
        )

    raise ComplaintConcurrentUpdateError(
        "The complaint changed while the edit " "was in progress. Reload it and retry."
    )


async def edit_generated_complaint_text(
    complaint_id,
    user_id,
    generated_text: str,
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )

    if current_status == "finalized":
        raise ComplaintFinalizedError("Finalized complaints cannot be edited.")

    if current_status == "draft":
        raise ComplaintNotGeneratedError(
            "Generate the complaint before editing " "the generated text."
        )

    if not existing.get("generated_text"):
        raise ComplaintNotGeneratedError("Generated complaint text is not available.")

    expected_revision = get_complaint_revision(existing)

    cleaned_text = generated_text.strip()

    if not cleaned_text:
        raise ComplaintStateError("Generated complaint text cannot be empty.")

    citation_result = validate_saved_complaint_citations(
        generated_text=cleaned_text,
        complaint=existing,
        require_legal_citation=False,
    )

    legal_validation = citation_result["legal_validation"]

    if not legal_validation["valid"]:
        raise ComplaintStateError(
            "The edited complaint contains unknown "
            "or invalid legal source citations."
        )

    evidence_validation = citation_result["evidence_validation"]

    if not evidence_validation["valid"]:
        raise ComplaintStateError(
            "The edited complaint contains unknown " "or invalid evidence citations."
        )

    updated = await update_complaint_if_unchanged(
        complaint_id=complaint_id,
        user_id=user_id,
        expected_revision=(expected_revision),
        expected_status=(current_status),
        update_data={
            "generated_text": cleaned_text,
            "status": "edited",
        },
    )

    if updated:
        return updated

    latest = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not latest:
        return None

    if (
        latest.get(
            "status",
            "draft",
        )
        == "finalized"
    ):
        raise ComplaintFinalizedError(
            "The complaint was finalized while "
            "the generated-text edit was in progress."
        )

    raise ComplaintConcurrentUpdateError(
        "The complaint changed while the "
        "generated-text edit was in progress. "
        "Reload it and retry."
    )


async def finalize_complaint(
    complaint_id,
    user_id,
    confirm: bool,
) -> dict[str, Any] | None:
    existing = await get_complaint(
        complaint_id=complaint_id,
        user_id=user_id,
    )

    if not existing:
        return None

    current_status = existing.get(
        "status",
        "draft",
    )
    expected_revision = get_complaint_revision(existing)

    if current_status == "finalized":
        raise ComplaintFinalizedError("Complaint has already been finalized.")

    if not confirm:
        raise ComplaintFinalizationError(
            "Explicit confirmation is required " "before finalizing the complaint."
        )

    if current_status not in {
        "generated",
        "edited",
    }:
        raise ComplaintNotGeneratedError("Generate the complaint before finalizing it.")

    generated_text = (existing.get("generated_text") or "").strip()

    if not generated_text:
        raise ComplaintNotGeneratedError("Generated complaint text is not available.")

    # =====================================================
    # 1. AUTHORITATIVE LEGAL SOURCE REQUIREMENT
    # =====================================================

    sources = existing.get(
        "sources",
        [],
    )

    if not sources:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized " "without authoritative legal sources."
        )

    allowed_legal_citations = get_allowed_legal_citations(existing)

    if not allowed_legal_citations:
        raise ComplaintFinalizationError(
            "The complaint does not contain valid " "legal source metadata."
        )

    # =====================================================
    # 2. CITATION INTEGRITY
    # =====================================================

    citation_result = validate_saved_complaint_citations(
        generated_text=generated_text,
        complaint=existing,
        require_legal_citation=True,
    )

    if not citation_result["legal_validation"]["valid"]:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized "
            "because its legal citations are invalid."
        )

    if not citation_result["used_legal_citations"]:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized "
            "because at least one authoritative "
            "legal citation is required."
        )

    if not citation_result["evidence_validation"]["valid"]:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized "
            "because its evidence citations are invalid."
        )

    used_evidence_citations = citation_result.get(
        "used_evidence_citations",
        [],
    )

    # -------------------------------------------------
    # CANONICAL CURRENT EVIDENCE SNAPSHOT
    # -------------------------------------------------

    used_evidence_references = get_used_evidence_references(
        complaint=existing,
        used_evidence_citations=(used_evidence_citations),
    )

    evidence_ids = [
        reference.get("evidence_id")
        for reference in used_evidence_references
        if reference.get("evidence_id")
    ]

    # =====================================================
    # 3. LOCK + CONSISTENCY + FINALIZE
    # =====================================================

    lock_token = None

    try:
        # -------------------------------------------------
        # 3A. LOCK EVERY CURRENTLY CITED EVIDENCE ITEM
        # -------------------------------------------------

        if evidence_ids:
            (
                lock_token,
                _locked_evidence,
            ) = await acquire_multiple_evidence_locks(
                evidence_ids=evidence_ids,
                user_id=user_id,
                operation="finalize_complaint",
            )

        # -------------------------------------------------
        # 3B. VALIDATE CONSISTENCY WHILE LOCKS ARE HELD
        # -------------------------------------------------

        evidence_consistency = await validate_complaint_evidence_consistency(
            complaint=existing,
            user_id=user_id,
            citation_ids=(used_evidence_citations),
        )

        if not evidence_consistency.get(
            "consistent",
            False,
        ):
            raise ComplaintFinalizationError(
                "The complaint cannot be finalized "
                "because one or more cited evidence "
                "items have changed, are unavailable, "
                "or no longer match the evidence "
                "snapshot used during generation. "
                "Regenerate the complaint before "
                "finalizing it."
            )

        # -------------------------------------------------
        # 3C. FINALIZE WHILE EVIDENCE IS STILL LOCKED
        # -------------------------------------------------

        finalized_at = datetime.now(timezone.utc)

        try:
            finalized = (
                await update_complaint_if_unchanged(
                    complaint_id=complaint_id,
                    user_id=user_id,
                    expected_revision=expected_revision,
                    expected_status=current_status,
                    update_data={
                        "status": "finalized",
                        "finalized_at": finalized_at,
                        "evidence_references":
                            used_evidence_references,
                    },
                )
            )

        except Exception as exc:
            # A network/database failure can make the exact
            # write outcome uncertain. Do not blindly retry
            # finalization from inside the service.
            raise ComplaintPersistenceError(
                "Complaint finalization could not be "
                "confirmed. Reload the complaint before "
                "trying again."
            ) from exc
        if not finalized:
            latest = await get_complaint(complaint_id=complaint_id, user_id=user_id)
            if not latest:
                raise ComplaintFinalizationError("The complaint no longer exists.")
            if latest.get("status", "draft") == "finalized":
                raise ComplaintFinalizedError(
                    "The complaint was finalized by another request."
                )

            raise ComplaintConcurrentUpdateError(
                "The complaint changed while finalization"
                "was in progress.Reload it and try again."
            )
        return finalized

    except EvidenceLifecycleBusyError as exc:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized while "
            "one or more cited evidence items are "
            "currently being changed. Try again shortly."
        ) from exc

    except EvidenceLifecycleReferenceError as exc:
        raise ComplaintFinalizationError(
            "The complaint cannot be finalized because "
            "one or more cited evidence items are no "
            "longer available."
        ) from exc

    finally:
        if lock_token is not None and evidence_ids:
            try:
                await release_multiple_evidence_locks(
                    evidence_ids=evidence_ids,
                    user_id=user_id,
                    lock_token=lock_token,
                )

            except Exception:
                # Do not hide a successful finalization
                # or the original finalization error.
                #
                # Lifecycle locks expire automatically.
                pass


async def remove_complaint(
    complaint_id,
    user_id,
) -> bool:
    lock_token = None
    locked_complaint = None

    try:
        # =================================================
        # 1. ACQUIRE SHARED COMPLAINT LIFECYCLE LEASE
        # =================================================

        try:
            (
                lock_token,
                locked_complaint,
            ) = await acquire_complaint_lock(
                complaint_id=complaint_id,
                user_id=user_id,
                operation="delete_complaint",
            )

        except ComplaintLifecycleReferenceError:
            return False

        except ComplaintLifecycleBusyError as exc:
            raise ComplaintConcurrentUpdateError(
                "The complaint is currently being changed. "
                "Try deleting it again shortly."
            ) from exc

        # From this point onward use the complaint returned
        # by the atomic lock acquisition.
        current_status = locked_complaint.get(
            "status",
            "draft",
        )

        if current_status == "finalized":
            raise ComplaintFinalizedError("Finalized complaints cannot be deleted.")

        expected_revision = get_complaint_revision(locked_complaint)

        # =================================================
        # 2. CHECK LINKED EVIDENCE WHILE LEASE IS HELD
        # =================================================

        linked_evidence_count = await count_evidence_for_complaint(
            complaint_id=(locked_complaint["_id"]),
            user_id=user_id,
        )

        if linked_evidence_count > 0:
            raise ComplaintHasEvidenceError(
                "Complaint cannot be deleted while " "evidence is still linked to it."
            )

        # =================================================
        # 3. CAS DELETE WHILE LEASE IS HELD
        # =================================================

        deleted = await delete_complaint_if_unchanged(
            complaint_id=(locked_complaint["_id"]),
            user_id=user_id,
            expected_revision=(expected_revision),
            expected_status=(current_status),
        )

        if deleted:
            return True

        # A complaint mutation may have happened while the
        # lifecycle lease was held. Those content mutations
        # use revision CAS independently.
        latest = await get_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
        )

        if not latest:
            return False

        if (
            latest.get(
                "status",
                "draft",
            )
            == "finalized"
        ):
            raise ComplaintFinalizedError(
                "The complaint was finalized while " "deletion was in progress."
            )

        latest_evidence_count = await count_evidence_for_complaint(
            complaint_id=latest["_id"],
            user_id=user_id,
        )

        if latest_evidence_count > 0:
            raise ComplaintHasEvidenceError(
                "Complaint cannot be deleted while " "evidence is still linked to it."
            )

        raise ComplaintConcurrentUpdateError(
            "The complaint changed while deletion "
            "was in progress. Reload it and retry."
        )

    finally:
        # If deletion succeeded, the complaint document is
        # already gone and release becomes a harmless no-op.
        if lock_token is not None and locked_complaint is not None:
            try:
                await release_complaint_lock(
                    complaint_id=(locked_complaint["_id"]),
                    user_id=user_id,
                    lock_token=lock_token,
                )

            except Exception:
                # Lease expiry provides stale-lock recovery.
                # Do not mask the original operation result.
                pass
