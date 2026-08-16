from datetime import datetime

from pydantic import BaseModel, Field


class ResourceCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=300,
    )
    category: str
    description: str = Field(
        min_length=1,
        max_length=2000,
    )
    url: str | None = None
    organization: str | None = Field(
        default=None,
        max_length=300,
    )


class ResourceResponse(BaseModel):
    id: str
    title: str
    category: str
    description: str
    url: str | None
    organization: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime