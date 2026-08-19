from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LegalCategory(str, Enum):
    CONSUMER_RIGHTS = "consumer_rights"
    LABOUR_RIGHTS = "labour_rights"
    WOMENS_SAFETY = "womens_safety"
    EDUCATIONAL_RIGHTS = "educational_rights"
    ANTI_RAGGING = "anti_ragging"


class ChatCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=150,
    )

    category: LegalCategory


class ChatUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    category: LegalCategory | None = None


class MessageCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=10000,
    )


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list[dict] = Field(
        default_factory=list
    )
    status: str = "completed"
    created_at: datetime


class ChatTurnResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class ChatResponse(BaseModel):
    id: str
    title: str
    category: LegalCategory
    created_at: datetime
    updated_at: datetime


class ChatDetailResponse(ChatResponse):
    messages: list[MessageResponse] = Field(
        default_factory=list
    )