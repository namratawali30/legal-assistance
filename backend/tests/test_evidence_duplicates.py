import uuid
from pathlib import Path

from app.services import (
    evidence_storage_service,
)


def unique_email() -> str:
    return (
        f"evidence-duplicate-"
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
                "Evidence Duplicate User",

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
    title: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(
            token
        ),
        json={
            "title":
                title,

            "category":
                "consumer_rights",

            "complainant_name":
                "Evidence Duplicate User",

            "complainant_address":
                "Test Address",

            "complainant_contact":
                "9999999999",

            "respondent_name":
                "ABC Seller",

            "respondent_address":
                "Seller Address",

            "incident_date":
                "2026-08-01",

            "incident_location":
                "Test City",

            "facts": (
                "I purchased a defective product "
                "and the seller refused to provide "
                "the requested refund or replacement."
            ),

            "relief_requested":
                "Refund or replacement.",

            "additional_details":
                {},
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def upload_evidence(
    client,
    token: str,
    content: bytes,
    complaint_id: str | None = None,
):
    data = {
        "title":
            "Duplicate evidence test",

        "description":
            "Testing duplicate-file protection.",
    }

    if complaint_id is not None:
        data[
            "complaint_id"
        ] = complaint_id

    return client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        data=data,
        files={
            "file": (
                "invoice.txt",
                content,
                "text/plain",
            )
        },
    )


def stored_files(
    upload_root: Path,
) -> list[Path]:
    evidence_root = (
        upload_root
        / "evidence"
    )

    if not evidence_root.exists():
        return []

    return [
        path
        for path in evidence_root.rglob(
            "*"
        )
        if path.is_file()
    ]


def configure_storage(
    monkeypatch,
    tmp_path,
) -> Path:
    upload_root = (
        tmp_path
        / "uploads"
    )

    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(upload_root),
    )

    return upload_root


def test_duplicate_library_upload_is_rejected_and_cleaned(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    content = (
        b"Invoice ABC-100 dated 1 August 2026 "
        b"for INR 25000."
    )

    first_response = upload_evidence(
        client=client,
        token=token,
        content=content,
    )

    assert first_response.status_code == 201, (
        first_response.text
    )

    assert len(
        stored_files(
            upload_root
        )
    ) == 1

    second_response = upload_evidence(
        client=client,
        token=token,
        content=content,
    )

    assert second_response.status_code == 409, (
        second_response.text
    )

    assert (
        "already been uploaded"
        in second_response.text.lower()
    )

    # The duplicate physical copy must have been
    # deleted. Only the original remains.
    assert len(
        stored_files(
            upload_root
        )
    ) == 1

    list_response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
    )

    assert list_response.status_code == 200

    matching_items = [
        item
        for item in list_response.json()
        if item[
            "sha256"
        ] == first_response.json()[
            "sha256"
        ]
        and item[
            "complaint_id"
        ] is None
    ]

    assert len(
        matching_items
    ) == 1


def test_same_file_can_be_linked_to_different_complaints(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    first_complaint = create_complaint(
        client,
        token,
        "First evidence complaint",
    )

    second_complaint = create_complaint(
        client,
        token,
        "Second evidence complaint",
    )

    content = (
        b"Common supporting document "
        b"relevant to two complaints."
    )

    first_response = upload_evidence(
        client=client,
        token=token,
        content=content,
        complaint_id=first_complaint[
            "id"
        ],
    )

    assert first_response.status_code == 201, (
        first_response.text
    )

    second_response = upload_evidence(
        client=client,
        token=token,
        content=content,
        complaint_id=second_complaint[
            "id"
        ],
    )

    assert second_response.status_code == 201, (
        second_response.text
    )

    first = first_response.json()
    second = second_response.json()

    assert (
        first["sha256"]
        == second["sha256"]
    )

    assert (
        first["complaint_id"]
        != second["complaint_id"]
    )

    # Separate complaint relationships currently
    # have separate stored artifacts.
    assert len(
        stored_files(
            upload_root
        )
    ) == 2


def test_same_file_duplicate_within_complaint_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
        "Duplicate evidence complaint",
    )

    content = (
        b"Receipt number DUPLICATE-001."
    )

    first_response = upload_evidence(
        client=client,
        token=token,
        content=content,
        complaint_id=complaint[
            "id"
        ],
    )

    assert first_response.status_code == 201, (
        first_response.text
    )

    second_response = upload_evidence(
        client=client,
        token=token,
        content=content,
        complaint_id=complaint[
            "id"
        ],
    )

    assert second_response.status_code == 409, (
        second_response.text
    )

    assert len(
        stored_files(
            upload_root
        )
    ) == 1

    list_response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        params={
            "complaint_id":
                complaint["id"]
        },
    )

    assert list_response.status_code == 200

    assert len(
        list_response.json()
    ) == 1