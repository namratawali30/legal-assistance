import hmac
from typing import Any

from app.rag.evidence_context import (
    hash_evidence_text,
    sanitize_evidence_text,
)
from app.repositories.evidence_repository import (
    get_evidence,
)
from app.services.evidence_text_extraction_service import (
    EvidenceExtractionError,
    verify_evidence_integrity,
)


class EvidenceConsistencyError(Exception):
    """Base exception for evidence consistency checks."""


def build_issue(
    citation_id: str | None,
    evidence_id: str | None,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "citation_id": citation_id,
        "evidence_id": evidence_id,
        "code": code,
        "message": message,
    }


async def validate_evidence_reference(
    reference: dict[str, Any],
    complaint_id,
    user_id,
) -> dict[str, Any]:
    """
    Validate one persisted complaint evidence reference
    against its current evidence record.

    This function does not mutate either record.
    """

    citation_id = reference.get("citation_id")

    evidence_id = reference.get("evidence_id")

    issues: list[dict[str, Any]] = []

    if not evidence_id:
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=None,
                code="missing_evidence_id",
                message=(
                    "The evidence snapshot does not " "contain an evidence identifier."
                ),
            )
        )

        return {
            "citation_id": citation_id,
            "evidence_id": None,
            "consistent": False,
            "issues": issues,
        }

    evidence = await get_evidence(
        evidence_id=evidence_id,
        user_id=user_id,
    )

    if not evidence:
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="evidence_missing",
                message=(
                    "The evidence record no longer " "exists or is not accessible."
                ),
            )
        )

        return {
            "citation_id": citation_id,
            "evidence_id": str(evidence_id),
            "consistent": False,
            "issues": issues,
        }

    # -------------------------------------------------
    # COMPLAINT LINKAGE
    # -------------------------------------------------

    current_complaint_id = evidence.get("complaint_id")

    if current_complaint_id is None or str(current_complaint_id) != str(complaint_id):
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="complaint_link_mismatch",
                message=("The evidence is no longer linked " "to this complaint."),
            )
        )

    snapshot_complaint_id = reference.get("complaint_id")

    if snapshot_complaint_id is not None and str(snapshot_complaint_id) != str(
        complaint_id
    ):
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="snapshot_complaint_mismatch",
                message=(
                    "The stored evidence snapshot " "references a different complaint."
                ),
            )
        )

    # -------------------------------------------------
    # PROCESSING STATE
    # -------------------------------------------------

    processing_status = evidence.get(
        "processing_status",
        "pending",
    )

    if processing_status != "ready":
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="evidence_not_ready",
                message=(
                    "The cited evidence is no longer " "in a ready processing state."
                ),
            )
        )

    # -------------------------------------------------
    # FILE SNAPSHOT
    # -------------------------------------------------

    snapshot_file_hash = reference.get("sha256")

    current_file_hash = evidence.get("sha256")

    if not snapshot_file_hash:
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="missing_file_snapshot",
                message=(
                    "The complaint evidence snapshot "
                    "does not contain a file fingerprint."
                ),
            )
        )

    elif not current_file_hash or not hmac.compare_digest(
        str(snapshot_file_hash),
        str(current_file_hash),
    ):
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="file_snapshot_mismatch",
                message=(
                    "The current evidence file fingerprint "
                    "does not match the complaint snapshot."
                ),
            )
        )

    # -------------------------------------------------
    # PHYSICAL FILE INTEGRITY
    # -------------------------------------------------

    try:
        verify_evidence_integrity(evidence)

    except EvidenceExtractionError:
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="physical_integrity_failure",
                message=("The stored evidence file failed " "its integrity check."),
            )
        )

    # -------------------------------------------------
    # EXTRACTED TEXT SNAPSHOT
    # -------------------------------------------------

    snapshot_text_hash = reference.get("extracted_text_sha256")

    current_text = evidence.get("extracted_text") or ""

    if not snapshot_text_hash:
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="missing_text_snapshot",
                message=(
                    "The complaint evidence snapshot "
                    "does not contain an extracted-text "
                    "fingerprint. Regeneration is required."
                ),
            )
        )

    elif not current_text.strip():
        issues.append(
            build_issue(
                citation_id=citation_id,
                evidence_id=str(evidence_id),
                code="extracted_text_missing",
                message=(
                    "The cited evidence no longer has " "extracted text available."
                ),
            )
        )

    else:
        normalized_text = sanitize_evidence_text(current_text)

        current_text_hash = hash_evidence_text(normalized_text)

        if not hmac.compare_digest(
            str(snapshot_text_hash),
            current_text_hash,
        ):
            issues.append(
                build_issue(
                    citation_id=citation_id,
                    evidence_id=str(evidence_id),
                    code="text_snapshot_mismatch",
                    message=(
                        "The extracted evidence text "
                        "has changed since complaint "
                        "generation."
                    ),
                )
            )

    return {
        "citation_id": citation_id,
        "evidence_id": str(evidence_id),
        "consistent": len(issues) == 0,
        "issues": issues,
        "current_processing_status": processing_status,
    }


async def validate_complaint_evidence_consistency(
    complaint: dict[str, Any],
    user_id,
    citation_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Validate persisted evidence snapshots against the
    current live evidence records.

    Modes:

    citation_ids is None
        Validate every persisted evidence reference.
        This is the audit / diagnostic mode.

    citation_ids is supplied
        Validate only those evidence references.
        Complaint finalization uses this mode so stale,
        unused snapshot metadata does not block
        finalization after a user removes an
        [EVIDENCE_n] citation from generated text.
    """

    complaint_id = complaint.get("_id")

    all_references = complaint.get(
        "evidence_references",
        [],
    )

    # -----------------------------------------------------
    # AUDIT MODE
    # -----------------------------------------------------
    #
    # None intentionally means ALL references.
    #
    # An empty list intentionally means NO evidence is
    # currently cited and therefore nothing needs checking.
    # -----------------------------------------------------

    if citation_ids is None:
        references = list(all_references)

        requested_citations = None

    else:
        requested_citations = {
            str(citation).upper() for citation in citation_ids if citation
        }

        if not requested_citations:
            return {
                "consistent": True,
                "has_evidence_references": bool(all_references),
                "checked_count": 0,
                "results": [],
                "issues": [],
            }

        references = [
            reference
            for reference in all_references
            if str(reference.get("citation_id", "")).upper() in requested_citations
        ]

        # Fail closed if final text cites an evidence ID
        # for which no persisted snapshot exists.
        available_citations = {
            str(reference.get("citation_id", "")).upper()
            for reference in references
            if reference.get("citation_id")
        }

        missing_citations = requested_citations - available_citations

        if missing_citations:
            issues = [
                build_issue(
                    citation_id=citation_id,
                    evidence_id=None,
                    code=("missing_evidence_reference"),
                    message=(
                        "A cited evidence identifier "
                        "has no persisted evidence "
                        "snapshot."
                    ),
                )
                for citation_id in sorted(missing_citations)
            ]

            return {
                "consistent": False,
                "has_evidence_references": bool(all_references),
                "checked_count": 0,
                "results": [],
                "issues": issues,
            }

    # -----------------------------------------------------
    # NOTHING TO VALIDATE
    # -----------------------------------------------------

    if not references:
        return {
            "consistent": True,
            "has_evidence_references": bool(all_references),
            "checked_count": 0,
            "results": [],
            "issues": [],
        }

    # -----------------------------------------------------
    # VALIDATE SNAPSHOTS
    # -----------------------------------------------------

    results: list[dict[str, Any]] = []

    all_issues: list[dict[str, Any]] = []

    for reference in references:
        result = await validate_evidence_reference(
            reference=reference,
            complaint_id=complaint_id,
            user_id=user_id,
        )

        results.append(result)

        all_issues.extend(
            result.get(
                "issues",
                [],
            )
        )

    return {
        "consistent": len(all_issues) == 0,
        "has_evidence_references": bool(all_references),
        "checked_count": len(results),
        "results": results,
        "issues": all_issues,
    }
