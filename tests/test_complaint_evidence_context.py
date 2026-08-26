import uuid

from bson import ObjectId

from app.services import (
    evidence_storage_service,
)
from app.services.complaint_evidence_context_service import (
    ComplaintEvidenceNotFoundError,
    build_complaint_evidence_context,
)


def unique_email() -> str:
    return (
        f"complaint-evidence-context-"
        f"{uuid.uuid4().hex[:10]}"
        "@example.com"
    )


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization":
            f"Bearer {token}"
    }


def create_account_and_token(
    client,
) -> str:
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name":
                "Complaint Evidence User",

            "email":
                email,

            "password":
                "TestPassword123!",
        },
    )

    assert register_response.status_code in (
        200,
        201,
    ), register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email":
                email,

            "password":
                "TestPassword123!",
        },
    )

    assert login_response.status_code == 200, (
        login_response.text
    )

    data = login_response.json()

    token = (
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )

    assert token

    return token


def create_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(
            token
        ),
        json={
            "title":
                "Evidence context complaint",

            "category":
                "consumer_rights",

            "complainant_name":
                "Complaint Evidence User",

            "complainant_address":
                "Test Address",

            "complainant_contact":
                "9999999999",

            "respondent_name":
                "ABC Electronics",

            "respondent_address":
                "Seller Address",

            "incident_date":
                "2026-08-01",

            "incident_location":
                "Test City",

            "facts": (
                "I purchased a defective product "
                "and requested a refund, but the "
                "seller refused my request."
            ),

            "relief_requested":
                "Refund of the purchase amount.",

            "additional_details":
                {},
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def upload_linked_evidence(
    client,
    token: str,
    complaint_id: str,
):
    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        data={
            "complaint_id":
                complaint_id,

            "title":
                "Purchase invoice",
        },
        files={
            "file": (
                "invoice.txt",
                (
                    b"Invoice number INV-700\n"
                    b"Amount paid: INR 27500"
                ),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_processed_linked_evidence_enters_context(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(
            tmp_path
            / "uploads"
        ),
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_linked_evidence(
        client,
        token,
        complaint[
            "id"
        ],
    )

    process_response = client.post(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}/process"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "retry":
                False
        },
    )

    assert process_response.status_code == 200, (
        process_response.text
    )

    assert process_response.json()[
        "processing_status"
    ] == "ready"

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    async def build():
        return await build_complaint_evidence_context(
            complaint_id=complaint[
                "id"
            ],
            user_id=user_id,
        )

    result = client.portal.call(
        build
    )

    assert result[
        "has_evidence"
    ] is True

    assert result[
        "included_count"
    ] == 1

    assert (
        "INV-700"
        in result[
            "context"
        ]
    )

    assert (
        "[EVIDENCE_1]"
        in result[
            "context"
        ]
    )


def test_pending_evidence_does_not_enter_context(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(
            tmp_path
            / "uploads"
        ),
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_linked_evidence(
        client,
        token,
        complaint[
            "id"
        ],
    )

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    async def build():
        return await build_complaint_evidence_context(
            complaint_id=complaint[
                "id"
            ],
            user_id=user_id,
        )

    result = client.portal.call(
        build
    )

    assert result[
        "has_evidence"
    ] is False

    assert result[
        "included_count"
    ] == 0

    assert result[
        "skipped"
    ][0][
        "reason"
    ] == "pending"


def test_other_user_cannot_build_complaint_context(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(
            tmp_path
            / "uploads"
        ),
    )

    owner_token = create_account_and_token(
        client
    )

    other_token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        owner_token,
    )

    # Obtain the other user's ObjectId from one
    # evidence record they own.
    other_complaint = create_complaint(
        client,
        other_token,
    )

    other_evidence = upload_linked_evidence(
        client,
        other_token,
        other_complaint[
            "id"
        ],
    )

    other_user_id = ObjectId(
        other_evidence[
            "user_id"
        ]
    )

    async def build():
        return await build_complaint_evidence_context(
            complaint_id=complaint[
                "id"
            ],
            user_id=other_user_id,
        )

    try:
        client.portal.call(
            build
        )

    except ComplaintEvidenceNotFoundError:
        pass

    else:
        raise AssertionError(
            "Another user unexpectedly obtained "
            "complaint evidence context."
        )