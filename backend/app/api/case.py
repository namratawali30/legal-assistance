from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any

from app.core.dependencies import get_current_user
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    SubmissionRecord,
    FollowUpReminder,
)
from app.services import case_service

router = APIRouter(
    prefix="/api/v1/cases",
    tags=["Cases"],
)


def format_case_response(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(case["_id"]),
        "user_id": str(case["user_id"]),
        "title": case.get("title", "Untitled Case"),
        "category": case.get("category", "consumer_rights"),
        "status": case.get("status", "intake"),
        "intake_facts": case.get("intake_facts", {}),
        "chat_session_ids": [str(c) for c in case.get("chat_session_ids", [])],
        "evidence_ids": [str(e) for e in case.get("evidence_ids", [])],
        "complaint_ids": [str(c) for c in case.get("complaint_ids", [])],
        "submission_record": case.get("submission_record"),
        "reminders": case.get("reminders", []),
        "activity_log": case.get("activity_log", []),
        "created_at": case["created_at"],
        "updated_at": case["updated_at"],
    }


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: dict = Depends(get_current_user),
):
    case = await case_service.create_new_case(
        user_id=str(current_user["_id"]),
        title=case_data.title,
        category=case_data.category.value if hasattr(case_data.category, "value") else str(case_data.category),
        intake_facts=case_data.intake_facts.model_dump() if case_data.intake_facts else {},
    )
    return format_case_response(case)


@router.get("", response_model=list[CaseResponse], status_code=status.HTTP_200_OK)
async def list_cases(
    current_user: dict = Depends(get_current_user),
):
    cases = await case_service.list_cases(user_id=str(current_user["_id"]))
    return [format_case_response(c) for c in cases]


@router.get("/{case_id}", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def get_case_detail(
    case_id: str,
    current_user: dict = Depends(get_current_user),
):
    case = await case_service.get_case_by_id(case_id, user_id=str(current_user["_id"]))
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    return format_case_response(case)


@router.patch("/{case_id}", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def update_case(
    case_id: str,
    case_data: CaseUpdate,
    current_user: dict = Depends(get_current_user),
):
    update_dict = case_data.model_dump(exclude_unset=True)
    if "category" in update_dict and hasattr(update_dict["category"], "value"):
        update_dict["category"] = update_dict["category"].value
    if "status" in update_dict and hasattr(update_dict["status"], "value"):
        update_dict["status"] = update_dict["status"].value

    updated = await case_service.update_case_details(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        update_data=update_dict,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or update failed",
        )
    return format_case_response(updated)


@router.post("/{case_id}/link-chat", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def link_chat(
    case_id: str,
    chat_session_id: str,
    current_user: dict = Depends(get_current_user),
):
    updated = await case_service.link_chat_to_case(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        chat_session_id=chat_session_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not link chat session to case",
        )
    return format_case_response(updated)


@router.post("/{case_id}/link-evidence", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def link_evidence(
    case_id: str,
    evidence_id: str,
    current_user: dict = Depends(get_current_user),
):
    updated = await case_service.link_evidence_to_case(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        evidence_id=evidence_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not link evidence to case",
        )
    return format_case_response(updated)


@router.post("/{case_id}/link-complaint", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def link_complaint(
    case_id: str,
    complaint_id: str,
    current_user: dict = Depends(get_current_user),
):
    updated = await case_service.link_complaint_to_case(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        complaint_id=complaint_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not link complaint draft to case",
        )
    return format_case_response(updated)


@router.post("/{case_id}/submission", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def record_case_submission(
    case_id: str,
    submission_data: SubmissionRecord,
    current_user: dict = Depends(get_current_user),
):
    updated = await case_service.record_submission(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        submission_data=submission_data.model_dump(),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or submission recording failed",
        )
    return format_case_response(updated)


@router.post("/{case_id}/reminders", response_model=CaseResponse, status_code=status.HTTP_200_OK)
async def add_case_reminder(
    case_id: str,
    reminder_data: FollowUpReminder,
    current_user: dict = Depends(get_current_user),
):
    updated = await case_service.add_reminder(
        case_id=case_id,
        user_id=str(current_user["_id"]),
        reminder_data=reminder_data.model_dump(),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or reminder creation failed",
        )
    return format_case_response(updated)
