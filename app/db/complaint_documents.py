from datetime import date, datetime, timezone
from typing import Any


def serialize_incident_date(
    value,
) -> str | None:
    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.date().isoformat()

    if isinstance(
        value,
        date,
    ):
        return value.isoformat()

    return str(value)


def build_complaint_document(
    user_id,
    title: str,
    category: str,
    complainant_name: str,
    respondent_name: str,
    facts: str,
    complainant_address: str | None = None,
    complainant_contact: str | None = None,
    respondent_address: str | None = None,
    incident_date=None,
    incident_location: str | None = None,
    relief_requested: str | None = None,
    additional_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(
        timezone.utc
    )

    return {
        "user_id":
            user_id,

        "title":
            title,

        "category":
            category,

        "complainant_name":
            complainant_name,

        "complainant_address":
            complainant_address,

        "complainant_contact":
            complainant_contact,

        "respondent_name":
            respondent_name,

        "respondent_address":
            respondent_address,

        "incident_date":
            serialize_incident_date(
                incident_date
            ),

        "incident_location":
            incident_location,

        "facts":
            facts,

        "relief_requested":
            relief_requested,

        "additional_details":
            additional_details or {},

        "generated_text":
            None,

        "sources":
            [],

        "status":
            "draft",

        "created_at":
            now,

        "updated_at":
            now,
    }