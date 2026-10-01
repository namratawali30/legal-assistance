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
    ComplaintExportGenerationError,
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
    safe_filename = (
        filename
        .replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
        .replace("\\", "_")
        .replace("/", "_")
        .strip()
    )

    if not safe_filename:
        safe_filename = (
            "complaint-export"
        )

    safe_filename = (
        safe_filename[:200]
    )

    return {
        "Content-Disposition": (
            "attachment; "
            f'filename="{safe_filename}"'
        ),
        "Cache-Control": (
            "no-store, no-cache, "
            "must-revalidate, private"
        ),
        "Pragma":
            "no-cache",

        "X-Content-Type-Options":
            "nosniff",
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
    except ComplaintExportGenerationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Complaint export could not be "
                "generated. Please try again later."
            ),
        ) from exc

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
    except ComplaintExportGenerationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Complaint export could not be "
                "generated. Please try again later."
            ),
        ) from exc

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