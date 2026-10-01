from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    ASK_FOLLOW_UP = "ASK_FOLLOW_UP"
    ANSWER = "ANSWER"
    REFUSE_UNSUPPORTED = "REFUSE_UNSUPPORTED"


class CaseContext(BaseModel):
    issue_type: str | None = None
    relationship: str | None = None
    category: str | None = None
    jurisdiction: str | None = None
    state_or_ut: str | None = None
    incident_type: str | None = None
    incident_date: str | None = None
    incident_location: str | None = None
    threats_or_coercion: str | None = None
    evidence_available: str | None = None
    steps_already_taken: str | None = None
    authority_already_contacted: str | None = None
    desired_outcome: str | None = None
    missing_facts: list[str] = Field(default_factory=list)


class ConversationDecision(BaseModel):
    action: DecisionAction
    question: str | None = None
    case_context_updates: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    reason_code: str = "DEFAULT"
    suggested_category: str | None = None
    suggested_options: list[str] | None = None
