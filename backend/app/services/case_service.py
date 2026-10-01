import uuid
from datetime import datetime, timezone
from typing import Any

from app.repositories import case_repository
from app.repositories.complaint_repository import get_complaint
from app.repositories.evidence_repository import get_evidence
from app.repositories.chat_repository import get_chat_session


async def create_new_case(user_id: str, title: str, category: str, intake_facts: dict | None = None) -> dict[str, Any]:
    case_data = {
        "user_id": str(user_id),
        "title": title,
        "category": category,
        "status": "intake",
        "intake_facts": intake_facts or {},
        "chat_session_ids": [],
        "evidence_ids": [],
        "complaint_ids": [],
        "reminders": [],
        "activity_log": [
            {
                "timestamp": datetime.now(timezone.utc),
                "action": "case_created",
                "actor_id": str(user_id),
                "details": f"Case created: {title}",
            }
        ],
    }
    created_doc = await case_repository.create_case(case_data)
    created_doc["id"] = str(created_doc["_id"])
    return created_doc


async def get_case_by_id(case_id: str, user_id: str) -> dict[str, Any] | None:
    return await case_repository.get_case(case_id, user_id)


async def list_cases(user_id: str) -> list[dict[str, Any]]:
    return await case_repository.get_user_cases(user_id)


async def update_case_details(case_id: str, user_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    updated = await case_repository.update_case(case_id, user_id, update_data)
    if updated:
        await case_repository.add_case_activity(case_id, user_id, "case_updated", "Updated case details")
    return updated


async def link_chat_to_case(case_id: str, user_id: str, chat_session_id: str) -> dict[str, Any] | None:
    case = await case_repository.get_case(case_id, user_id)
    if not case:
        return None
    chat = await get_chat_session(chat_session_id, user_id)
    if not chat:
        return None

    chat_ids = set(case.get("chat_session_ids", []))
    chat_ids.add(str(chat_session_id))
    updated = await case_repository.update_case(case_id, user_id, {"chat_session_ids": list(chat_ids)})
    await case_repository.add_case_activity(case_id, user_id, "chat_linked", f"Linked chat session {chat_session_id}")
    return updated


async def link_evidence_to_case(case_id: str, user_id: str, evidence_id: str) -> dict[str, Any] | None:
    case = await case_repository.get_case(case_id, user_id)
    if not case:
        return None
    evidence = await get_evidence(evidence_id, user_id)
    if not evidence:
        return None

    ev_ids = set(case.get("evidence_ids", []))
    ev_ids.add(str(evidence_id))
    updated = await case_repository.update_case(case_id, user_id, {"evidence_ids": list(ev_ids)})
    await case_repository.add_case_activity(case_id, user_id, "evidence_linked", f"Linked evidence item {evidence_id}")
    return updated


async def link_complaint_to_case(case_id: str, user_id: str, complaint_id: str) -> dict[str, Any] | None:
    case = await case_repository.get_case(case_id, user_id)
    if not case:
        return None
    complaint = await get_complaint(complaint_id, user_id)
    if not complaint:
        return None

    c_ids = set(case.get("complaint_ids", []))
    c_ids.add(str(complaint_id))
    updated = await case_repository.update_case(case_id, user_id, {"complaint_ids": list(c_ids)})
    await case_repository.add_case_activity(case_id, user_id, "complaint_linked", f"Linked complaint draft {complaint_id}")
    return updated


async def record_submission(case_id: str, user_id: str, submission_data: dict[str, Any]) -> dict[str, Any] | None:
    case = await case_repository.get_case(case_id, user_id)
    if not case:
        return None

    submission_record = {
        "authority_name": submission_data["authority_name"],
        "submission_date": submission_data["submission_date"],
        "reference_number": submission_data.get("reference_number"),
        "notes": submission_data.get("notes"),
        "acknowledged_by_user": True,
        "recorded_at": datetime.now(timezone.utc),
    }

    updated = await case_repository.update_case(
        case_id,
        user_id,
        {
            "submission_record": submission_record,
            "status": "submitted",
        },
    )
    await case_repository.add_case_activity(
        case_id,
        user_id,
        "submission_recorded",
        f"User recorded submission to {submission_data['authority_name']} (Ref: {submission_data.get('reference_number', 'N/A')})",
    )
    return updated


async def add_reminder(case_id: str, user_id: str, reminder_data: dict[str, Any]) -> dict[str, Any] | None:
    case = await case_repository.get_case(case_id, user_id)
    if not case:
        return None

    reminders = list(case.get("reminders", []))
    new_reminder = {
        "id": str(uuid.uuid4()),
        "title": reminder_data["title"],
        "due_date": reminder_data["due_date"],
        "status": reminder_data.get("status", "pending"),
        "notes": reminder_data.get("notes"),
        "created_at": datetime.now(timezone.utc),
    }
    reminders.append(new_reminder)

    updated = await case_repository.update_case(case_id, user_id, {"reminders": reminders})
    await case_repository.add_case_activity(case_id, user_id, "reminder_added", f"Added reminder: {reminder_data['title']}")
    return updated
