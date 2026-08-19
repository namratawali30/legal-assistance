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
from app.services.complaint_export_service import (
    ComplaintExportContentError,
    ComplaintNotFinalizedError,
    export_complaint_docx,
    export_complaint_pdf,
)


router = APIRouter(
    prefix="/api/v1/complaints",
    tags=["Complaint Exports"],
)


def build_download_headers(
    filename: str,
) -> dict[str, str]:
    return {
        "Content-Disposition": (
            f'attachment; filename="{filename}"'
        ),
        "Cache-Control": (
            "no-store, no-cache, "
            "must-revalidate, private"
        ),
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
    }


@router.get(
    "/{complaint_id}/export/pdf",
    response_class=Response,
)
async def export_complaint_pdf_endpoint(
    complaint_id: str,
    current_user: dict = Depends(
        get_current_user
    ),
):
    try:
        result = await export_complaint_pdf(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
        )

    except ComplaintNotFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintExportContentError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    content, filename = result

    return Response(
        content=content,
        media_type="application/pdf",
        headers=build_download_headers(
            filename
        ),
    )


@router.get(
    "/{complaint_id}/export/docx",
    response_class=Response,
)
async def export_complaint_docx_endpoint(
    complaint_id: str,
    current_user: dict = Depends(
        get_current_user
    ),
):
    try:
        result = await export_complaint_docx(
            complaint_id=complaint_id,
            user_id=current_user["_id"],
        )

    except ComplaintNotFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except ComplaintExportContentError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    content, filename = result

    return Response(
        content=content,
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers=build_download_headers(
            filename
        ),
    )