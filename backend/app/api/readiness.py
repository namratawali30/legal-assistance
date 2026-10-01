from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.dependencies import get_current_user
from app.repositories.chat_repository import get_chat_session
from app.repositories.complaint_repository import get_complaint
from app.schemas.readiness import CaseReadinessResponse
from app.services.case_readiness_service import (
    compute_complaint_readiness,
    compute_session_readiness,
)

router = APIRouter(prefix="/api/v1/readiness", tags=["readiness"])


@router.get(
    "/session/{session_id}",
    response_model=CaseReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_session_readiness(
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
        return await compute_session_readiness(
            session=session,
            user_id=current_user["_id"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Case readiness could not be assessed right now.",
        ) from exc


@router.get(
    "/complaint/{complaint_id}",
    response_model=CaseReadinessResponse,
    status_code=status.HTTP_200_OK,
)
async def get_complaint_readiness(
    complaint_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(complaint_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid complaint ID format",
        )

    complaint = await get_complaint(complaint_id, current_user["_id"])

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    try:
        return await compute_complaint_readiness(
            complaint=complaint,
            user_id=current_user["_id"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Case readiness could not be assessed right now.",
        ) from exc
