import uuid


def unique_email() -> str:
    return (
        f"evidence-lifecycle-"
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
                "Evidence Lifecycle User",

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
                "Complaint with evidence",

            "category":
                "consumer_rights",

            "complainant_name":
                "Evidence Lifecycle User",

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
                "a refund or replacement despite "
                "my request."
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
                "Invoice",

            "description":
                "Purchase invoice",
        },
        files={
            "file": (
                "invoice.txt",
                b"Invoice ABC-123 for INR 25000.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_complaint_with_evidence_cannot_be_deleted(
    client,
    monkeypatch,
    tmp_path,
):
    from app.services import (
        evidence_storage_service,
    )

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

    evidence = upload_evidence(
        client,
        token,
        complaint[
            "id"
        ],
    )

    delete_response = client.delete(
        (
            "/api/v1/complaints/"
            f"{complaint['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert delete_response.status_code == 409, (
        delete_response.text
    )

    assert (
        "evidence"
        in delete_response.text.lower()
    )

    # Complaint must still exist.
    complaint_response = client.get(
        (
            "/api/v1/complaints/"
            f"{complaint['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert complaint_response.status_code == 200

    # Remove the linked evidence first.
    evidence_delete_response = client.delete(
        (
            "/api/v1/evidence/"
            f"{evidence['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert (
        evidence_delete_response.status_code
        == 204
    ), evidence_delete_response.text

    # Complaint can now be removed.
    delete_response = client.delete(
        (
            "/api/v1/complaints/"
            f"{complaint['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert delete_response.status_code == 204, (
        delete_response.text
    )

    complaint_response = client.get(
        (
            "/api/v1/complaints/"
            f"{complaint['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert complaint_response.status_code == 404