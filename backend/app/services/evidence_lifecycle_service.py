from app.repositories.complaint_repository import (
    get_finalized_complaint_citing_evidence,
)


class EvidenceLifecycleError(Exception):
    """Base error for evidence lifecycle restrictions."""


class EvidenceLockedByFinalizedComplaintError(
    EvidenceLifecycleError
):
    """
    Raised when evidence is protected because a finalized
    complaint cites it.
    """


async def ensure_evidence_not_finalized_locked(
    evidence_id,
    user_id,
) -> None:
    complaint = (
        await get_finalized_complaint_citing_evidence(
            evidence_id=evidence_id,
            user_id=user_id,
        )
    )

    if complaint:
        raise EvidenceLockedByFinalizedComplaintError(
            "This evidence is cited by a finalized "
            "complaint and cannot be deleted or "
            "reprocessed."
        )