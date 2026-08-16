from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(
        default="New Legal Consultation",
        min_length=1,
        max_length=200,
    )
    category: str


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    category: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=10000,
    )


class MessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    role: str
    content: str
    sources: list[dict] = []
    created_at: datetime