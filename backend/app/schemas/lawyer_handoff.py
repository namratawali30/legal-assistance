from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class HandoffParty(BaseModel):
    role: str  # "Complainant", "Respondent", etc.
    name: str
    organization: str | None = None
    contact_details: str | None = None
    address: str | None = None


class HandoffTimelineEvent(BaseModel):
    date_or_approx: str
    event: str
    certainty: str = "established"  # "established", "approximate", "unverified"


class HandoffFact(BaseModel):
    label: str
    provenance: list[str] = Field(default_factory=list)


class HandoffQuestion(BaseModel):
    label: str
    reason: str | None = None


class HandoffEvidenceItem(BaseModel):
    citation_id: str  # e.g. "EVIDENCE_1"
    title: str
    original_filename: str
    evidence_type: str
    media_type: str
    size_bytes: int
    sha256: str
    processing_status: str
    transcript_available: bool = False
    transcript_sha256: str | None = None


class HandoffComplaintInfo(BaseModel):
    status: str  # "none", "draft", "generated", "edited", "finalized"
    title: str | None = None
    is_finalized: bool = False
    generated_text_preview: str | None = None


class HandoffLegalSource(BaseModel):
    citation_id: str  # e.g. "SOURCE_1"
    title: str
    authority: str | None = None
    provision_type: str | None = None
    provision_number: str | None = None
    official_url: str | None = None
    last_verified: str | None = None


class LawyerHandoffResponse(BaseModel):
    case_summary: str
    parties: list[HandoffParty] = Field(default_factory=list)
    user_objective: str
    chronology: list[HandoffTimelineEvent] = Field(default_factory=list)
    established_facts: list[HandoffFact] = Field(default_factory=list)
    unresolved_questions: list[HandoffQuestion] = Field(default_factory=list)
    evidence_index: list[HandoffEvidenceItem] = Field(default_factory=list)
    complaint_summary: HandoffComplaintInfo
    legal_sources: list[HandoffLegalSource] = Field(default_factory=list)
    actions_already_taken: list[str] = Field(default_factory=list)
    current_next_step: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

