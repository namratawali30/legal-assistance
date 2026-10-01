from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)

from app.core.dependencies import (
    get_current_user,
)
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintFinalizeRequest,
    ComplaintGenerateRequest,
    ComplaintGeneratedTextUpdate,
    ComplaintResponse,
    ComplaintUpdate,
)
from app.services.complaint_generation_service import (
    ComplaintAlreadyGeneratedError,
    ComplaintGenerationConflictError,
    ComplaintGenerationPersistenceError,
    ComplaintInsufficientContextError,
    ComplaintFinalizedGenerationError,
    ComplaintLLMUnavailableError,
    generate_complaint_for_user,
)

from app.services.complaint_service import (
    ComplaintConcurrentUpdateError,
    ComplaintFinalizationError,
    ComplaintFinalizedError,
    ComplaintHasEvidenceError,
    ComplaintNotGeneratedError,
    ComplaintPersistenceError,
    ComplaintStateError,
    create_complaint_draft,
    edit_generated_complaint_text,
    finalize_complaint,
    find_complaint,
    list_user_complaints,
    remove_complaint,
    update_complaint_draft,
)

router = APIRouter(
    prefix="/api/v1/complaints",
    tags=["Complaints"],
)


def serialize_complaint(
    complaint: dict,
) -> dict:
    return {
        "id": str(complaint["_id"]),
        "user_id": str(complaint["user_id"]),
        "title": complaint["title"],
        "category": complaint["category"],
        "complainant_name": complaint["complainant_name"],
        "complainant_address": complaint.get("complainant_address"),
        "complainant_contact": complaint.get("complainant_contact"),
        "respondent_name": complaint["respondent_name"],
        "respondent_address": complaint.get("respondent_address"),
        "incident_date": complaint.get("incident_date"),
        "incident_location": complaint.get("incident_location"),
        "facts": complaint["facts"],
        "relief_requested": complaint.get("relief_requested"),
        "additional_details": complaint.get(
            "additional_details",
            {},
        ),
        "generated_text": complaint.get("generated_text"),
        "sources": complaint.get(
            "sources",
            [],
        ),
        "evidence_references": [
            serialize_evidence_reference(reference)
            for reference in complaint.get(
                "evidence_references",
                [],
            )
        ],
        "status": complaint.get(
            "status",
            "draft",
        ),
        "generated_at": complaint.get("generated_at"),
        "finalized_at": complaint.get("finalized_at"),
        "created_at": complaint["created_at"],
        "updated_at": complaint["updated_at"],
    }


def serialize_evidence_reference(
    reference: dict,
) -> dict:
    return {
        "citation_id": reference.get("citation_id"),
        "evidence_id": reference.get("evidence_id"),
        "complaint_id": reference.get("complaint_id"),
        "title": reference.get("title"),
        "original_filename": reference.get("original_filename"),
        "evidence_type": reference.get("evidence_type"),
        "media_type": reference.get("media_type"),
        "sha256": reference.get("sha256"),
        "extracted_text_sha256":reference.get("extracted_text_sha256"),
        "extraction_method": reference.get("extraction_method"),
        "extracted_page_count": reference.get("extracted_page_count"),
        "included_characters": reference.get(
            "included_characters",
            0,
        ),
        "truncated": reference.get(
            "truncated",
            False,
        ),
    }


# =========================================================
# CREATE COMPLAINT
# =========================================================


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_complaint_endpoint(
    complaint_data: ComplaintCreate,
    current_user: dict = Depends(get_current_user),
):
    complaint = await create_complaint_draft(
        user_id=current_user["_id"],
        complaint_data=(complaint_data.model_dump()),
    )

    if not complaint:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=("Could not create complaint"),
        )

    return serialize_complaint(complaint)


# =========================================================
# LIST COMPLAINTS
# =========================================================


@router.get(
    "",
    response_model=list[ComplaintResponse],
)
async def list_complaints_endpoint(
    current_user: dict = Depends(get_current_user),
):
    complaints = await list_user_complaints(user_id=current_user["_id"])

    return [serialize_complaint(complaint) for complaint in complaints]


# =========================================================
# GENERATE / REGENERATE COMPLAINT
# =========================================================


@router.post(
    "/{complaint_id}/generate",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_complaint_endpoint(
    complaint_id: str,
    request: ComplaintGenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        complaint = await generate_complaint_for_user(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
            regenerate=request.regenerate,
        )

    except ComplaintAlreadyGeneratedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintInsufficientContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except ComplaintGenerationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ComplaintLLMUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Complaint generation is temporarily "
                "unavailable. Please try again later."
            ),
        ) from exc
    except ComplaintConcurrentUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ComplaintFinalizedGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ComplaintGenerationPersistenceError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "The generated complaint could not "
                "be saved. Please reload and try again."
            ),
        ) from exc

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return serialize_complaint(complaint)


# =========================================================
# EDIT GENERATED COMPLAINT TEXT
# =========================================================


@router.patch(
    "/{complaint_id}/generated-text",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
)
async def update_generated_text_endpoint(
    complaint_id: str,
    request: ComplaintGeneratedTextUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        complaint = await edit_generated_complaint_text(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
            generated_text=(request.generated_text),
        )

    except ComplaintFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintNotGeneratedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ComplaintConcurrentUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return serialize_complaint(complaint)


# =========================================================
# FINALIZE COMPLAINT
# =========================================================


@router.post(
    "/{complaint_id}/finalize",
    response_model=ComplaintResponse,
    status_code=status.HTTP_200_OK,
)
async def finalize_complaint_endpoint(
    complaint_id: str,
    request: ComplaintFinalizeRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        complaint = await finalize_complaint(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
            confirm=request.confirm,
        )

    except ComplaintFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintNotGeneratedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintPersistenceError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Complaint finalization could not "
                "be confirmed. Reload the complaint "
                "before trying again."
            ),
        ) from exc

    except ComplaintFinalizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return serialize_complaint(complaint)


# =========================================================
# GET COMPLAINT
# =========================================================


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
async def get_complaint_endpoint(
    complaint_id: str,
    current_user: dict = Depends(get_current_user),
):
    complaint = await find_complaint(
        complaint_id=complaint_id,
        user_id=current_user["_id"],
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return serialize_complaint(complaint)


# =========================================================
# UPDATE STRUCTURED COMPLAINT DATA
# =========================================================


@router.patch(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
async def update_complaint_endpoint(
    complaint_id: str,
    complaint_data: ComplaintUpdate,
    current_user: dict = Depends(get_current_user),
):
    update_data = complaint_data.model_dump(exclude_unset=True)

    try:
        complaint = await update_complaint_draft(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
            update_data=update_data,
        )

    except ComplaintFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ComplaintConcurrentUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return serialize_complaint(complaint)


# =========================================================
# DELETE COMPLAINT
# =========================================================
@router.delete(
    "/{complaint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_complaint_endpoint(
    complaint_id: str,
    current_user: dict = Depends(
        get_current_user
    ),
):
    try:
        deleted = await remove_complaint(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
        )

    except ComplaintFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintConcurrentUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintHasEvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )