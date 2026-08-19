from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chat import LegalCategory


class ComplaintStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    EDITED = "edited"
    FINALIZED = "finalized"


class ComplaintCreate(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=200,
    )

    category: LegalCategory

    complainant_name: str = Field(
        min_length=2,
        max_length=150,
    )

    complainant_address: str | None = Field(
        default=None,
        max_length=1000,
    )

    complainant_contact: str | None = Field(
        default=None,
        max_length=100,
    )

    respondent_name: str = Field(
        min_length=2,
        max_length=200,
    )

    respondent_address: str | None = Field(
        default=None,
        max_length=1000,
    )

    incident_date: date | None = None

    incident_location: str | None = Field(
        default=None,
        max_length=500,
    )

    facts: str = Field(
        min_length=20,
        max_length=15000,
    )

    relief_requested: str | None = Field(
        default=None,
        max_length=5000,
    )

    additional_details: dict[str, Any] = Field(
        default_factory=dict,
    )


class ComplaintUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    complainant_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    complainant_address: str | None = Field(
        default=None,
        max_length=1000,
    )

    complainant_contact: str | None = Field(
        default=None,
        max_length=100,
    )

    respondent_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    respondent_address: str | None = Field(
        default=None,
        max_length=1000,
    )

    incident_date: date | None = None

    incident_location: str | None = Field(
        default=None,
        max_length=500,
    )

    facts: str | None = Field(
        default=None,
        min_length=20,
        max_length=15000,
    )

    relief_requested: str | None = Field(
        default=None,
        max_length=5000,
    )

    additional_details: dict[str, Any] | None = None


class ComplaintGenerateRequest(BaseModel):
    regenerate: bool = False


class ComplaintGeneratedTextUpdate(BaseModel):
    generated_text: str = Field(
        min_length=20,
        max_length=30000,
    )


class ComplaintFinalizeRequest(BaseModel):
    confirm: bool


class ComplaintSource(BaseModel):
    citation_id: str

    title: str

    authority: str

    category: str | None = None

    provision_type: str | None = None

    provision_number: str | None = None

    provision_title: str | None = None

    page_start: int | None = None

    page_end: int | None = None

    landing_page: str | None = None

    pdf_url: str | None = None


class ComplaintResponse(BaseModel):
    id: str
    user_id: str

    title: str
    category: LegalCategory

    complainant_name: str
    complainant_address: str | None = None
    complainant_contact: str | None = None

    respondent_name: str
    respondent_address: str | None = None

    incident_date: date | None = None
    incident_location: str | None = None

    facts: str
    relief_requested: str | None = None

    additional_details: dict[str, Any] = Field(
        default_factory=dict,
    )

    generated_text: str | None = None

    sources: list[ComplaintSource] = Field(
        default_factory=list,
    )

    status: ComplaintStatus

    generated_at: datetime | None = None
    finalized_at: datetime | None = None

    created_at: datetime
    updated_at: datetime