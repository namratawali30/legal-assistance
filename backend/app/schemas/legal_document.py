from datetime import datetime

from pydantic import BaseModel, Field


class LegalDocumentCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=300,
    )
    category: str
    source: str = Field(
        min_length=1,
        max_length=500,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class LegalDocumentResponse(BaseModel):
    id: str
    title: str
    category: str
    source: str
    description: str | None
    document_type: str
    version: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime