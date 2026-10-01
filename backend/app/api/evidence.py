from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.core.dependencies import (
    get_current_user,
)
from app.core.evidence_validation import (
    EvidenceValidationError,
)
from app.schemas.evidence import (
    EvidenceProcessRequest,
    EvidenceResponse,
    EvidenceUpdate,
)
import app.services.evidence_processing_service
from app.services.evidence_service import (
    EvidenceComplaintNotFoundError,
    EvidenceDeleteError,
    EvidenceDuplicateError,
    EvidenceComplaintBusyError,
    EvidenceFileUnavailableError,
    EvidenceIntegrityError,
    EvidencePersistenceError,
    create_evidence_for_user,
    find_evidence,
    list_evidence_for_user,
    prepare_evidence_download,
    remove_evidence,
    update_evidence_metadata,
)
from app.services.evidence_storage_service import (
    EvidencePathError,
    EvidenceStorageError,
    EvidenceTooLargeError,
    EvidenceWriteError,
)
from app.services.evidence_lifecycle_service import (
    EvidenceLockedByFinalizedComplaintError,
)
from app.services.evidence_lifecycle_lock_service import (
    EvidenceLifecycleBusyError,
    EvidenceLifecycleReferenceError,
)

router = APIRouter(
    prefix="/api/v1/evidence",
    tags=["Evidence"],
)


def serialize_evidence(
    evidence: dict,
) -> dict:
    complaint_id = evidence.get("complaint_id")

    return {
        "id": str(evidence["_id"]),
        "user_id": str(evidence["user_id"]),
        "complaint_id": (str(complaint_id) if complaint_id else None),
        "title": evidence.get("title"),
        "description": evidence.get("description"),
        "original_filename": evidence["original_filename"],
        "evidence_type": evidence["evidence_type"],
        "media_type": evidence["media_type"],
        "file_extension": evidence["file_extension"],
        "size_bytes": evidence["size_bytes"],
        "sha256": evidence["sha256"],
        "status": evidence.get(
            "status",
            "uploaded",
        ),
        "processing_status": evidence.get(
            "processing_status",
            "pending",
        ),
        "extraction_method": evidence.get("extraction_method"),
        "extracted_character_count": evidence.get(
            "extracted_character_count",
            0,
        ),
        "extracted_page_count": evidence.get("extracted_page_count"),
        "processed_at": evidence.get("processed_at"),
        "processing_error": evidence.get("processing_error"),
        # extracted_text is deliberately private.
        "created_at": evidence["created_at"],
        "updated_at": evidence["updated_at"],
    }


# =========================================================
# UPLOAD
# =========================================================


from app.services.rate_limiter import rate_limiter
from app.services.quota_service import QuotaExceededError
from app.services.evidence_storage_service import EvidenceInfectedError


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence_endpoint(
    file: UploadFile = File(...),
    complaint_id: str | None = Form(default=None),
    title: str | None = Form(
        default=None,
        max_length=200,
    ),
    description: str | None = Form(
        default=None,
        max_length=2000,
    ),
    current_user: dict = Depends(get_current_user),
):
    await rate_limiter.check_rate_limit(f"evidence_upload:{current_user['_id']}", max_requests=20, window_seconds=60)

    if complaint_id is not None:
        complaint_id = complaint_id.strip() or None

    if title is not None:
        title = title.strip() or None

    if description is not None:
        description = description.strip() or None

    try:
        evidence = await create_evidence_for_user(
            upload=file,
            user_id=current_user["_id"],
            complaint_id=complaint_id,
            title=title,
            description=description,
        )

    except EvidenceComplaintNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except EvidenceComplaintBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except EvidenceDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except EvidenceTooLargeError as exc:
        raise HTTPException(
            status_code=(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
            detail=str(exc),
        )

    except EvidenceInfectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except EvidenceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except (
        EvidencePathError,
        EvidenceWriteError,
        EvidenceStorageError,
    ) as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=("Evidence could not be stored securely."),
        ) from exc

    except EvidencePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Evidence could not be saved."
            ),
        ) from exc

    return serialize_evidence(evidence)


# =========================================================
# LIST
# =========================================================


@router.get(
    "",
    response_model=list[EvidenceResponse],
)
async def list_evidence_endpoint(
    complaint_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    if complaint_id is not None:
        complaint_id = complaint_id.strip() or None

    try:
        evidence_items = await list_evidence_for_user(
            user_id=current_user["_id"],
            complaint_id=complaint_id,
        )

    except EvidenceComplaintNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return [serialize_evidence(evidence) for evidence in evidence_items]


# =========================================================
# PROCESS
# =========================================================


@router.post(
    "/{evidence_id}/process",
    response_model=EvidenceResponse,
)
async def process_evidence_endpoint(
    evidence_id: str,
    request: EvidenceProcessRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        evidence = (
            await app.services.evidence_processing_service.process_evidence_for_user(
                evidence_id=evidence_id,
                user_id=current_user["_id"],
                retry=request.retry,
            )
        )

    except (
        app.services.evidence_processing_service.EvidenceProcessingInProgressError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except (
        app.services.evidence_processing_service.EvidenceAlreadyProcessedError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except (
    app.services.evidence_processing_service
    .EvidenceProcessingPersistenceError
) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Evidence processing could not "
                "be completed."
            ),
        ) from exc
    except EvidenceLockedByFinalizedComplaintError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except (
    app.services.evidence_processing_service
    .EvidenceProcessingError
) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Evidence processing could not "
                "be completed."
            ),
        ) from exc
    except EvidenceLifecycleBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except EvidenceLifecycleReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return serialize_evidence(evidence)


# =========================================================
# DOWNLOAD
# =========================================================


@router.get(
    "/{evidence_id}/download",
)
async def download_evidence_endpoint(
    evidence_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        result = await prepare_evidence_download(
            evidence_id=evidence_id,
            user_id=current_user["_id"],
        )

    except EvidenceIntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except EvidenceFileUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    evidence, path = result

    return FileResponse(
        path=path,
        media_type=evidence["media_type"],
        filename=evidence["original_filename"],
        headers={
            "Cache-Control": ("no-store, no-cache, " "must-revalidate, private"),
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


# =========================================================
# GET METADATA
# =========================================================


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
)
async def get_evidence_endpoint(
    evidence_id: str,
    current_user: dict = Depends(get_current_user),
):
    evidence = await find_evidence(
        evidence_id=evidence_id,
        user_id=current_user["_id"],
    )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return serialize_evidence(evidence)


# =========================================================
# UPDATE METADATA
# =========================================================


@router.patch(
    "/{evidence_id}",
    response_model=EvidenceResponse,
)
async def update_evidence_endpoint(
    evidence_id: str,
    update_data: EvidenceUpdate,
    current_user: dict = Depends(get_current_user),
):
    evidence = await update_evidence_metadata(
        evidence_id=evidence_id,
        user_id=current_user["_id"],
        update_data=(update_data.model_dump(exclude_unset=True)),
    )

    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return serialize_evidence(evidence)


# =========================================================
# DELETE
# =========================================================


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_evidence_endpoint(
    evidence_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        deleted = await remove_evidence(
            evidence_id=evidence_id,
            user_id=current_user["_id"],
        )

    except EvidenceDeleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Evidence could not be deleted."
            ),
        ) from exc
    except EvidenceLockedByFinalizedComplaintError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except EvidencePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Evidence could not be deleted."
            ),
        ) from exc
    except EvidenceLifecycleBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except EvidenceLifecycleReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
