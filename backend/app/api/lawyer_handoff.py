from fastapi import APIRouter, Depends, HTTPException, Response, status
from bson import ObjectId

from app.core.dependencies import get_current_user
from app.repositories.chat_repository import get_chat_session
from app.schemas.lawyer_handoff import LawyerHandoffResponse
from app.services.lawyer_handoff_service import (
    build_handoff_docx_export,
    build_handoff_pdf_export,
    generate_session_handoff_pack,
)

router = APIRouter(prefix="/api/v1/lawyer-handoff", tags=["lawyer-handoff"])


@router.get(
    "/session/{session_id}",
    response_model=LawyerHandoffResponse,
    status_code=status.HTTP_200_OK,
)
async def get_session_lawyer_handoff(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await get_chat_session(session_id, current_user["_id"])

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    try:
        return await generate_session_handoff_pack(
            session=session,
            user_id=current_user["_id"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lawyer handoff pack could not be generated right now.",
        ) from exc


@router.get(
    "/session/{session_id}/export/pdf",
    status_code=status.HTTP_200_OK,
)
async def export_session_handoff_pdf(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await get_chat_session(session_id, current_user["_id"])

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    pack = await generate_session_handoff_pack(session, current_user["_id"])
    pdf_bytes = build_handoff_pdf_export(pack)

    headers = {
        "Content-Disposition": f'attachment; filename="lawyer_handoff_{session_id}.pdf"',
        "Cache-Control": "no-store, private",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get(
    "/session/{session_id}/export/docx",
    status_code=status.HTTP_200_OK,
)
async def export_session_handoff_docx(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = await get_chat_session(session_id, current_user["_id"])

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    pack = await generate_session_handoff_pack(session, current_user["_id"])
    docx_bytes = build_handoff_docx_export(pack)

    headers = {
        "Content-Disposition": f'attachment; filename="lawyer_handoff_{session_id}.docx"',
        "Cache-Control": "no-store, private",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
