import json
import math
import re

from datetime import (
    date,
    datetime,
)
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
)

from app.schemas.chat import (
    LegalCategory,
)


_DISALLOWED_CONTROL_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
)

MAX_ADDITIONAL_DETAILS_BYTES = (
    32 * 1024
)

MAX_ADDITIONAL_DETAILS_DEPTH = 5

MAX_ADDITIONAL_DETAILS_ITEMS = 100

MAX_ADDITIONAL_DETAILS_KEY_LENGTH = (
    100
)

MAX_ADDITIONAL_DETAILS_STRING_LENGTH = (
    5000
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


def validate_additional_details_node(
    value: Any,
    *,
    depth: int = 0,
) -> None:
    if (
        depth
        > MAX_ADDITIONAL_DETAILS_DEPTH
    ):
        raise ValueError(
            "additional_details is nested "
            "too deeply."
        )

    if isinstance(
        value,
        dict,
    ):
        if (
            len(value)
            > MAX_ADDITIONAL_DETAILS_ITEMS
        ):
            raise ValueError(
                "additional_details contains "
                "too many items."
            )

        for key, nested_value in (
            value.items()
        ):
            if not isinstance(
                key,
                str,
            ):
                raise ValueError(
                    "additional_details keys "
                    "must be strings."
                )

            if not key.strip():
                raise ValueError(
                    "additional_details keys "
                    "cannot be blank."
                )

            if (
                len(key)
                > MAX_ADDITIONAL_DETAILS_KEY_LENGTH
            ):
                raise ValueError(
                    "An additional_details key "
                    "is too long."
                )

            validate_safe_text(
                key
            )

            validate_additional_details_node(
                nested_value,
                depth=depth + 1,
            )

        return

    if isinstance(
        value,
        list,
    ):
        if (
            len(value)
            > MAX_ADDITIONAL_DETAILS_ITEMS
        ):
            raise ValueError(
                "An additional_details list "
                "contains too many items."
            )

        for nested_value in value:
            validate_additional_details_node(
                nested_value,
                depth=depth + 1,
            )

        return

    if isinstance(
        value,
        str,
    ):
        if (
            len(value)
            > MAX_ADDITIONAL_DETAILS_STRING_LENGTH
        ):
            raise ValueError(
                "An additional_details text "
                "value is too long."
            )

        validate_safe_text(
            value
        )

        return

    if value is None:
        return

    if isinstance(
        value,
        bool,
    ):
        return

    if isinstance(
        value,
        int,
    ):
        return

    if isinstance(
        value,
        float,
    ):
        if not math.isfinite(
            value
        ):
            raise ValueError(
                "additional_details cannot "
                "contain non-finite numbers."
            )

        return

    raise ValueError(
        "additional_details contains "
        "an unsupported value type."
    )


def validate_additional_details(
    value: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if value is None:
        return None

    validate_additional_details_node(
        value
    )

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "additional_details must contain "
            "valid JSON-compatible values."
        ) from exc

    if (
        len(encoded)
        > MAX_ADDITIONAL_DETAILS_BYTES
    ):
        raise ValueError(
            "additional_details exceeds "
            "the maximum allowed size."
        )

    return value


class StrictComplaintRequest(
    BaseModel
):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ComplaintStatus(
    str,
    Enum,
):
    DRAFT = "draft"

    GENERATED = "generated"

    EDITED = "edited"

    FINALIZED = "finalized"


class ComplaintCreate(
    StrictComplaintRequest
):
    title: str = Field(
        min_length=3,
        max_length=200,
    )

    category: LegalCategory

    complainant_name: str = Field(
        min_length=2,
        max_length=150,
    )

    complainant_address: (
        str
        | None
    ) = Field(
        default=None,
        max_length=1000,
    )

    complainant_contact: (
        str
        | None
    ) = Field(
        default=None,
        max_length=100,
    )

    respondent_name: str = Field(
        min_length=2,
        max_length=200,
    )

    respondent_address: (
        str
        | None
    ) = Field(
        default=None,
        max_length=1000,
    )

    incident_date: (
        date
        | None
    ) = None

    incident_location: (
        str
        | None
    ) = Field(
        default=None,
        max_length=500,
    )

    facts: str = Field(
        min_length=20,
        max_length=15000,
    )

    relief_requested: (
        str
        | None
    ) = Field(
        default=None,
        max_length=5000,
    )

    additional_details: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )

    @field_validator(
        "title",
        "complainant_name",
        "respondent_name",
        "facts",
    )
    @classmethod
    def validate_required_text(
        cls,
        value: str,
    ) -> str:
        return validate_safe_text(
            value
        )

    @field_validator(
        "complainant_address",
        "complainant_contact",
        "respondent_address",
        "incident_location",
        "relief_requested",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(
            value
        )

    @field_validator(
        "additional_details"
    )
    @classmethod
    def validate_details(
        cls,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        return (
            validate_additional_details(
                value
            )
            or {}
        )


class ComplaintUpdate(
    StrictComplaintRequest
):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
    )

    complainant_name: (
        str
        | None
    ) = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    complainant_address: (
        str
        | None
    ) = Field(
        default=None,
        max_length=1000,
    )

    complainant_contact: (
        str
        | None
    ) = Field(
        default=None,
        max_length=100,
    )

    respondent_name: (
        str
        | None
    ) = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    respondent_address: (
        str
        | None
    ) = Field(
        default=None,
        max_length=1000,
    )

    incident_date: (
        date
        | None
    ) = None

    incident_location: (
        str
        | None
    ) = Field(
        default=None,
        max_length=500,
    )

    facts: str | None = Field(
        default=None,
        min_length=20,
        max_length=15000,
    )

    relief_requested: (
        str
        | None
    ) = Field(
        default=None,
        max_length=5000,
    )

    additional_details: (
        dict[str, Any]
        | None
    ) = None

    @field_validator(
        "title",
        "complainant_name",
        "respondent_name",
        "facts",
    )
    @classmethod
    def validate_required_when_present(
        cls,
        value: str | None,
    ) -> str | None:
        return validate_safe_text(
            value
        )

    @field_validator(
        "complainant_address",
        "complainant_contact",
        "respondent_address",
        "incident_location",
        "relief_requested",
    )
    @classmethod
    def validate_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_optional_text(
            value
        )

    @field_validator(
        "additional_details"
    )
    @classmethod
    def validate_details(
        cls,
        value: (
            dict[str, Any]
            | None
        ),
    ) -> (
        dict[str, Any]
        | None
    ):
        return validate_additional_details(
            value
        )


class ComplaintGenerateRequest(
    StrictComplaintRequest
):
    regenerate: StrictBool = False


class ComplaintGeneratedTextUpdate(
    StrictComplaintRequest
):
    generated_text: str = Field(
        min_length=20,
        max_length=30000,
    )

    @field_validator(
        "generated_text"
    )
    @classmethod
    def validate_generated_text(
        cls,
        value: str,
    ) -> str:
        return validate_safe_text(
            value
        )


class ComplaintFinalizeRequest(
    StrictComplaintRequest
):
    confirm: StrictBool


class ComplaintSource(BaseModel):
    citation_id: str

    title: str

    authority: str

    category: str | None = None

    provision_type: (
        str
        | None
    ) = None

    provision_number: (
        str
        | None
    ) = None

    provision_title: (
        str
        | None
    ) = None

    page_start: int | None = None

    page_end: int | None = None

    landing_page: (
        str
        | None
    ) = None

    pdf_url: str | None = None


class ComplaintEvidenceReference(
    BaseModel
):
    citation_id: str

    evidence_id: str

    complaint_id: (
        str
        | None
    ) = None

    title: str | None = None

    original_filename: (
        str
        | None
    ) = None

    evidence_type: (
        str
        | None
    ) = None

    media_type: (
        str
        | None
    ) = None

    sha256: str | None = None

    extracted_text_sha256: (
        str
        | None
    ) = None

    extraction_method: (
        str
        | None
    ) = None

    extracted_page_count: (
        int
        | None
    ) = None

    included_characters: int = 0

    truncated: bool = False


class ComplaintResponse(BaseModel):
    id: str

    user_id: str

    title: str

    category: LegalCategory

    complainant_name: str

    complainant_address: (
        str
        | None
    ) = None

    complainant_contact: (
        str
        | None
    ) = None

    respondent_name: str

    respondent_address: (
        str
        | None
    ) = None

    incident_date: (
        date
        | None
    ) = None

    incident_location: (
        str
        | None
    ) = None

    facts: str

    relief_requested: (
        str
        | None
    ) = None

    additional_details: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )

    generated_text: (
        str
        | None
    ) = None

    sources: list[
        ComplaintSource
    ] = Field(
        default_factory=list,
    )

    status: ComplaintStatus

    generated_at: (
        datetime
        | None
    ) = None

    finalized_at: (
        datetime
        | None
    ) = None

    created_at: datetime

    updated_at: datetime

    evidence_references: list[
        ComplaintEvidenceReference
    ] = Field(
        default_factory=list
    )