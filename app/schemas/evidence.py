import re

from datetime import datetime
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
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


def normalize_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return validate_safe_text(
        value
    )


class StrictEvidenceRequest(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class EvidenceType(
    str,
    Enum,
):
    DOCUMENT = "document"

    IMAGE = "image"

    TEXT = "text"

    OTHER = "other"


class EvidenceStatus(
    str,
    Enum,
):
    UPLOADED = "uploaded"

    DELETED = "deleted"


class EvidenceProcessingStatus(
    str,
    Enum,
):
    PENDING = "pending"

    PROCESSING = "processing"

    READY = "ready"

    NO_TEXT = "no_text"

    REQUIRES_OCR = (
        "requires_ocr"
    )

    FAILED = "failed"


class EvidenceCreateMetadata(
    StrictEvidenceRequest
):
    complaint_id: (
        str
        | None
    ) = None

    title: str | None = Field(
        default=None,
        max_length=200,
    )

    description: (
        str
        | None
    ) = Field(
        default=None,
        max_length=2000,
    )

    @field_validator(
        "complaint_id",
        "title",
        "description",
    )
    @classmethod
    def normalize_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(
            value
        )


class EvidenceUpdate(
    StrictEvidenceRequest
):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: (
        str
        | None
    ) = Field(
        default=None,
        max_length=2000,
    )

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

    @field_validator(
        "description"
    )
    @classmethod
    def validate_description(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(
            value
        )


class EvidenceProcessRequest(
    StrictEvidenceRequest
):
    retry: StrictBool = False


class EvidenceResponse(BaseModel):
    id: str

    user_id: str

    complaint_id: (
        str
        | None
    ) = None

    title: str | None = None

    description: (
        str
        | None
    ) = None

    original_filename: str

    evidence_type: EvidenceType

    media_type: str

    file_extension: str

    size_bytes: int

    sha256: str

    status: EvidenceStatus

    processing_status: (
        EvidenceProcessingStatus
    )

    extraction_method: (
        str
        | None
    ) = None

    extracted_character_count: (
        int
    ) = 0

    extracted_page_count: (
        int
        | None
    ) = None

    processed_at: (
        datetime
        | None
    ) = None

    processing_error: (
        str
        | None
    ) = None

    created_at: datetime

    updated_at: datetime