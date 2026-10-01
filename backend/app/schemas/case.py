from datetime import datetime, date
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import LegalCategory


class CaseStatus(str, Enum):
    INTAKE = "intake"
    ACTIVE = "active"
    DRAFTING = "drafting"
    UNDER_REVIEW = "under_review"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"
    SUBMITTED = "submitted"
    CLOSED = "closed"


class IntakeFacts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    complainant_name: str | None = Field(default=None, max_length=200)
    complainant_address: str | None = Field(default=None, max_length=500)
    complainant_phone: str | None = Field(default=None, max_length=50)
    complainant_email: str | None = Field(default=None, max_length=200)

    opposite_party_name: str | None = Field(default=None, max_length=200)
    opposite_party_address: str | None = Field(default=None, max_length=500)

    incident_date: str | None = Field(default=None, max_length=100)
    incident_location: str | None = Field(default=None, max_length=200)

    transaction_amount: float | None = Field(default=None, ge=0.0)
    transaction_details: str | None = Field(default=None, max_length=5000)

    desired_outcome: str | None = Field(default=None, max_length=2000)
    narrative_summary: str | None = Field(default=None, max_length=10000)
    missing_information: list[str] = Field(default_factory=list)


class SubmissionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authority_name: str = Field(min_length=1, max_length=300)
    submission_date: str = Field(min_length=1, max_length=100)
    reference_number: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    acknowledged_by_user: bool = Field(default=True)


class FollowUpReminder(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    due_date: str = Field(min_length=1, max_length=100)
    status: str = Field(default="pending", max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    created_at: datetime | None = None


class CaseActivity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: datetime
    action: str
    actor_id: str
    details: str | None = None


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    category: LegalCategory = Field(default=LegalCategory.CONSUMER_RIGHTS)
    intake_facts: IntakeFacts | None = None


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: LegalCategory | None = None
    status: CaseStatus | None = None
    intake_facts: IntakeFacts | None = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    title: str
    category: str
    status: CaseStatus
    intake_facts: IntakeFacts
    chat_session_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    complaint_ids: list[str] = Field(default_factory=list)
    submission_record: SubmissionRecord | None = None
    reminders: list[FollowUpReminder] = Field(default_factory=list)
    activity_log: list[CaseActivity] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
