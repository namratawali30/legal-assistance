from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class CaseReadinessState(str, Enum):
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    READY_FOR_NEXT_STEP = "READY_FOR_NEXT_STEP"


class FactEstablished(BaseModel):
    label: str
    status: str = "established"
    provenance: list[str] = Field(default_factory=list)


class FactMissing(BaseModel):
    label: str
    importance: str = "high"  # "high", "medium", "optional"
    reason: str | None = None


class EvidenceAvailableItem(BaseModel):
    evidence_id: str
    title: str
    status: str  # "ready", "pending", "processing", "no_text", "requires_ocr", "failed"
    supports: str | None = None


class EvidenceGapItem(BaseModel):
    label: str
    recommendation: str


class CaseReadinessResponse(BaseModel):
    readiness_state: CaseReadinessState
    facts_established: list[FactEstablished] = Field(default_factory=list)
    facts_missing: list[FactMissing] = Field(default_factory=list)
    evidence_available: list[EvidenceAvailableItem] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGapItem] = Field(default_factory=list)
    legal_sources: list[dict[str, Any]] = Field(default_factory=list)
    possible_authority: str | None = None
    next_step: str
