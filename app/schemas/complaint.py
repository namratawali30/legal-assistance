from datetime import datetime

from pydantic import BaseModel, Field


class ComplaintCreate(BaseModel):
    category: str
    title: str = Field(
        min_length=5,
        max_length=200,
    )
    description: str = Field(
        min_length=20,
        max_length=10000,
    )


class ComplaintUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=5,
        max_length=200,
    )
    description: str | None = Field(
        default=None,
        min_length=20,
        max_length=10000,
    )
    status: str | None = None


class ComplaintResponse(BaseModel):
    id: str
    user_id: str
    category: str
    title: str
    description: str
    status: str
    generated_draft: str | None
    created_at: datetime
    updated_at: datetime