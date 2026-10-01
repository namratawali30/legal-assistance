from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.dependencies import get_current_user
from app.repositories.chat_repository import get_chat_session
from app.repositories.complaint_repository import get_complaint
from app.schemas.action_plan import ActionPlanResponse
from app.services.legal_action_planner_service import (
    generate_complaint_action_plan,
    generate_session_action_plan,
)

router = APIRouter(prefix="/api/v1/action-plan", tags=["action-plan"])


@router.get(
    "/session/{session_id}",
    response_model=ActionPlanResponse,
    status_code=status.HTTP_200_OK,
)
async def get_session_action_plan(
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
        return await generate_session_action_plan(
            session=session,
            user_id=current_user["_id"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action plan could not be generated right now.",
        ) from exc


@router.get(
    "/complaint/{complaint_id}",
    response_model=ActionPlanResponse,
    status_code=status.HTTP_200_OK,
)
async def get_complaint_action_plan(
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
        return await generate_complaint_action_plan(
            complaint=complaint,
            user_id=current_user["_id"],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action plan could not be generated right now.",
        ) from exc
