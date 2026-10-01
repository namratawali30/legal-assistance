from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class PlanStatus(str, Enum):
    NEEDS_MORE_INFORMATION = "NEEDS_MORE_INFORMATION"
    NOT_READY = "NOT_READY"
    PLAN_AVAILABLE = "PLAN_AVAILABLE"


class ActionStepState(str, Enum):
    TODO = "TODO"
    DONE = "DONE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ActionStep(BaseModel):
    order: int
    title: str
    instruction: str
    reason: str | None = None
    source_citations: list[str] = Field(default_factory=list)  # e.g. ["SOURCE_1"]
    evidence_citations: list[str] = Field(default_factory=list)  # e.g. ["EVIDENCE_1"]
    priority: str = "medium"  # "high", "medium", "low"
    state: ActionStepState = ActionStepState.TODO


class ActionPlanResponse(BaseModel):
    status: PlanStatus
    steps: list[ActionStep] = Field(default_factory=list)
    primary_next_step: str
    important_caution: str | None = None
