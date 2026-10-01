import re
from datetime import datetime
from enum import Enum
from typing import Any


from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


_DISALLOWED_CONTROL_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
)


def validate_safe_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    if _DISALLOWED_CONTROL_CHARS.search(
        value
    ):
        raise ValueError(
            "Text contains unsupported "
            "control characters."
        )

    return value


class StrictChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class LegalCategory(str, Enum):
    CONSUMER_RIGHTS = "consumer_rights"
    LABOUR_RIGHTS = "labour_rights"
    WOMENS_SAFETY = "womens_safety"
    EDUCATIONAL_RIGHTS = "educational_rights"
    ANTI_RAGGING = "anti_ragging"


class AnswerMode(str, Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"


class ChatCreate(
    StrictChatRequest
):
    title: str = Field(
        min_length=1,
        max_length=150,
    )

    category: LegalCategory

    answer_mode: AnswerMode = AnswerMode.SIMPLE

    @field_validator(
        "title"
    )
    @classmethod
    def validate_title(
        cls,
        value: str,
    ) -> str:
        return validate_safe_text(
            value
        )


class ChatUpdate(
    StrictChatRequest
):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )

    category: (
        LegalCategory
        | None
    ) = None

    answer_mode: AnswerMode | None = None

    @field_validator(
        "title"
    )
    @classmethod
    def validate_title(
        cls,
        value: str | None,
    ) -> str | None:
        return validate_safe_text(
            value
        )


class MessageCreate(
    StrictChatRequest
):
    content: str = Field(
        min_length=1,
        max_length=10000,
    )

    answer_mode: AnswerMode | None = None


    @field_validator(
        "content"
    )
    @classmethod
    def validate_content(
        cls,
        value: str,
    ) -> str:
        return validate_safe_text(
            value
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

    message_type: str = "answer"

    suggested_options: list[str] | None = None

    category_notice: str | None = None

    created_at: datetime



class ChatTurnResponse(BaseModel):
    user_message: MessageResponse

    assistant_message: (
        MessageResponse
    )


class ChatResponse(BaseModel):
    id: str

    title: str

    category: LegalCategory

    answer_mode: AnswerMode = AnswerMode.SIMPLE

    case_context: dict[str, Any] = Field(
        default_factory=dict
    )

    clarification_count: int = 0

    created_at: datetime

    updated_at: datetime



class ChatDetailResponse(
    ChatResponse
):
    messages: list[
        MessageResponse
    ] = Field(
        default_factory=list
    )