import hashlib
import uuid
from pathlib import Path

from app.services import (
    evidence_storage_service,
)


# =========================================================
# HELPERS
# =========================================================


def unique_email() -> str:
    token = uuid.uuid4().hex[:10]

    return (
        f"evidence-test-"
        f"{token}@example.com"
    )


def register_user(
    client,
):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name":
                "Evidence Test User",

            "email":
                email,

            "password":
                "TestPassword123!",
        },
    )

    assert response.status_code in (
        200,
        201,
    ), response.text

    return {
        "email":
            email,

        "password":
            "TestPassword123!",
    }


def login_user(
    client,
    email: str,
    password: str,
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email":
                email,

            "password":
                password,
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    data = response.json()

    token = (
        data.get("access_token")
        or data.get("token")
    )

    assert token

    return token


def create_account_and_token(
    client,
) -> str:
    account = register_user(
        client
    )

    return login_user(
        client,
        account["email"],
        account["password"],
    )


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization":
            f"Bearer {token}"
    }


def configure_test_storage(
    monkeypatch,
    tmp_path: Path,
):
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
                "Evidence-linked complaint",

            "category":
                "consumer_rights",

            "complainant_name":
                "Evidence Test User",

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
                "from the respondent and requested "
                "a refund, but the respondent did "
                "not provide the requested remedy."
            ),

            "relief_requested":
                "Refund of the purchase amount.",

            "additional_details": {},
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def upload_text_evidence(
    client,
    token: str,
    content: bytes,
    complaint_id: str | None = None,
    filename: str = "evidence.txt",
):
    data = {
        "title":
            "Test evidence",

        "description":
            "Evidence uploaded by regression test.",
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
                filename,
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
        for path in evidence_root.rglob("*")
        if path.is_file()
    ]


# =========================================================
# AUTHENTICATION
# =========================================================


def test_evidence_endpoints_require_authentication(
    client,
):
    response = client.get(
        "/api/v1/evidence"
    )

    assert response.status_code in (
        401,
        403,
    )

    response = client.post(
        "/api/v1/evidence",
        files={
            "file": (
                "evidence.txt",
                b"private evidence",
                "text/plain",
            )
        },
    )

    assert response.status_code in (
        401,
        403,
    )


# =========================================================
# VALID UPLOAD + SHA-256 + DOWNLOAD
# =========================================================


def test_upload_and_download_preserve_integrity(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    content = (
        b"Invoice number ABC-123. "
        b"Payment amount was INR 25000."
    )

    response = upload_text_evidence(
        client=client,
        token=token,
        content=content,
        filename="invoice.txt",
    )

    assert response.status_code == 201, (
        response.text
    )

    evidence = response.json()

    assert evidence[
        "original_filename"
    ] == "invoice.txt"

    assert evidence[
        "file_extension"
    ] == ".txt"

    assert evidence[
        "media_type"
    ] == "text/plain"

    assert evidence[
        "evidence_type"
    ] == "text"

    assert evidence[
        "size_bytes"
    ] == len(content)

    expected_hash = hashlib.sha256(
        content
    ).hexdigest()

    assert evidence[
        "sha256"
    ] == expected_hash

    # Internal filesystem details must never
    # leak through the public API.
    assert (
        "storage_path"
        not in evidence
    )

    assert (
        "stored_filename"
        not in evidence
    )

    files = stored_files(
        upload_root
    )

    assert len(files) == 1

    # Randomized server filename should not reuse
    # the user's original filename.
    assert files[0].name != (
        "invoice.txt"
    )

    evidence_id = evidence[
        "id"
    ]

    download_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}/download"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert (
        download_response.status_code
        == 200
    ), download_response.text

    assert (
        download_response.content
        == content
    )

    assert (
        download_response.headers[
            "content-type"
        ].startswith(
            "text/plain"
        )
    )

    disposition = (
        download_response.headers.get(
            "content-disposition",
            "",
        )
    )

    assert (
        "attachment"
        in disposition.lower()
    )

    assert (
        "invoice.txt"
        in disposition
    )

    cache_control = (
        download_response.headers.get(
            "cache-control",
            "",
        ).lower()
    )

    assert "no-store" in cache_control
    assert "private" in cache_control

    assert (
        download_response.headers.get(
            "x-content-type-options"
        )
        == "nosniff"
    )


# =========================================================
# FAKE PDF
# =========================================================


def test_fake_pdf_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "fake.pdf",
                b"This is not actually a PDF.",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400, (
        response.text
    )

    assert (
        "valid pdf"
        in response.text.lower()
    )

    # Invalid uploads must not leave files behind.
    assert stored_files(
        upload_root
    ) == []


# =========================================================
# MIME MISMATCH
# =========================================================


def test_extension_media_type_mismatch_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "evidence.pdf",
                b"\xff\xd8\xfffake-jpeg-data",
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 400, (
        response.text
    )

    assert (
        "does not match"
        in response.text.lower()
    )

    assert stored_files(
        upload_root
    ) == []


# =========================================================
# PATH TRAVERSAL
# =========================================================


def test_traversal_filename_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "../secret.txt",
                b"attempted traversal",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400, (
        response.text
    )

    assert stored_files(
        upload_root
    ) == []

    # Nothing should have escaped into the
    # temporary test directory either.
    assert not (
        tmp_path
        / "secret.txt"
    ).exists()


# =========================================================
# SIZE LIMIT
# =========================================================


def test_oversized_upload_is_rejected_and_cleaned_up(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    # Temporarily reduce the limit to 1 MiB so
    # the test stays fast and memory-efficient.
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "max_upload_size_mb",
        1,
    )

    token = create_account_and_token(
        client
    )

    content = (
        b"A"
        * (
            1024
            * 1024
            + 1
        )
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "large.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 413, (
        response.text
    )

    assert stored_files(
        upload_root
    ) == []


# =========================================================
# COMPLAINT OWNERSHIP
# =========================================================


def test_evidence_cannot_link_to_another_users_complaint(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    owner_token = create_account_and_token(
        client
    )

    attacker_token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        owner_token,
    )

    response = upload_text_evidence(
        client=client,
        token=attacker_token,
        content=(
            b"This must never be linked "
            b"to another user's complaint."
        ),
        complaint_id=complaint[
            "id"
        ],
    )

    # Do not disclose another user's
    # complaint existence.
    assert response.status_code == 404, (
        response.text
    )

    # Ownership is checked before filesystem write.
    assert stored_files(
        upload_root
    ) == []


def test_owned_complaint_can_receive_evidence(
    client,
    monkeypatch,
    tmp_path,
):
    configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    response = upload_text_evidence(
        client=client,
        token=token,
        content=(
            b"Invoice supporting the "
            b"consumer complaint."
        ),
        complaint_id=complaint[
            "id"
        ],
    )

    assert response.status_code == 201, (
        response.text
    )

    evidence = response.json()

    assert evidence[
        "complaint_id"
    ] == complaint[
        "id"
    ]

    list_response = client.get(
        "/api/v1/evidence",
        params={
            "complaint_id":
                complaint["id"]
        },
        headers=auth_headers(
            token
        ),
    )

    assert list_response.status_code == 200, (
        list_response.text
    )

    items = list_response.json()

    assert any(
        item["id"]
        == evidence["id"]
        for item in items
    )


# =========================================================
# CROSS-USER ISOLATION
# =========================================================


def test_cross_user_evidence_access_is_blocked(
    client,
    monkeypatch,
    tmp_path,
):
    configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    owner_token = create_account_and_token(
        client
    )

    other_token = create_account_and_token(
        client
    )

    upload_response = (
        upload_text_evidence(
            client=client,
            token=owner_token,
            content=(
                b"Private evidence belonging "
                b"only to the owner."
            ),
        )
    )

    assert (
        upload_response.status_code
        == 201
    ), upload_response.text

    evidence_id = (
        upload_response.json()[
            "id"
        ]
    )

    other_headers = auth_headers(
        other_token
    )

    get_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=other_headers,
    )

    assert (
        get_response.status_code
        == 404
    )

    download_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}/download"
        ),
        headers=other_headers,
    )

    assert (
        download_response.status_code
        == 404
    )

    patch_response = client.patch(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=other_headers,
        json={
            "title":
                "Unauthorized modification"
        },
    )

    assert (
        patch_response.status_code
        == 404
    )

    delete_response = client.delete(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=other_headers,
    )

    assert (
        delete_response.status_code
        == 404
    )

    # Owner should still have access.
    owner_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=auth_headers(
            owner_token
        ),
    )

    assert (
        owner_response.status_code
        == 200
    )


# =========================================================
# METADATA UPDATE
# =========================================================


def test_evidence_metadata_can_be_updated(
    client,
    monkeypatch,
    tmp_path,
):
    configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    upload_response = (
        upload_text_evidence(
            client=client,
            token=token,
            content=b"Metadata update test.",
        )
    )

    assert (
        upload_response.status_code
        == 201
    )

    evidence = (
        upload_response.json()
    )

    original_hash = evidence[
        "sha256"
    ]

    original_size = evidence[
        "size_bytes"
    ]

    response = client.patch(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "title":
                "Updated evidence title",

            "description":
                "Updated evidence description",
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    updated = response.json()

    assert updated[
        "title"
    ] == "Updated evidence title"

    assert updated[
        "description"
    ] == (
        "Updated evidence description"
    )

    # File identity metadata must remain unchanged.
    assert updated[
        "sha256"
    ] == original_hash

    assert updated[
        "size_bytes"
    ] == original_size


# =========================================================
# FILE INTEGRITY CHECK
# =========================================================


def test_tampered_stored_file_is_not_downloaded(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    response = upload_text_evidence(
        client=client,
        token=token,
        content=b"Original evidence content.",
    )

    assert response.status_code == 201, (
        response.text
    )

    evidence_id = response.json()[
        "id"
    ]

    files = stored_files(
        upload_root
    )

    assert len(files) == 1

    # Simulate unexpected filesystem tampering.
    files[0].write_bytes(
        b"Tampered evidence content!"
    )

    download_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}/download"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert (
        download_response.status_code
        == 409
    )

    assert (
        "integrity"
        in download_response.text.lower()
    )


# =========================================================
# DELETE FILE + METADATA
# =========================================================


def test_delete_removes_file_and_metadata(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    response = upload_text_evidence(
        client=client,
        token=token,
        content=b"Evidence to delete.",
    )

    assert response.status_code == 201, (
        response.text
    )

    evidence_id = response.json()[
        "id"
    ]

    assert len(
        stored_files(
            upload_root
        )
    ) == 1

    delete_response = client.delete(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert (
        delete_response.status_code
        == 204
    ), delete_response.text

    assert stored_files(
        upload_root
    ) == []

    metadata_response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert (
        metadata_response.status_code
        == 404
    )


# =========================================================
# DATABASE FAILURE / ORPHAN CLEANUP
# =========================================================


def test_database_insert_failure_cleans_up_stored_file(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = configure_test_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    async def fail_create_evidence(
        evidence_data,
    ):
        raise RuntimeError(
            "Simulated database failure"
        )

    monkeypatch.setattr(
        (
            "app.services."
            "evidence_service."
            "create_evidence"
        ),
        fail_create_evidence,
    )

    response = upload_text_evidence(
        client=client,
        token=token,
        content=(
            b"This physical file must be "
            b"removed after DB failure."
        ),
    )

    assert response.status_code == 500, (
        response.text
    )

    # Critical rollback guarantee:
    # database failure must not leave an
    # orphaned private evidence file.
    assert stored_files(
        upload_root
    ) == []


# =========================================================
# INVALID IDS
# =========================================================


def test_invalid_evidence_id_returns_404(
    client,
):
    token = create_account_and_token(
        client
    )

    headers = auth_headers(
        token
    )

    response = client.get(
        (
            "/api/v1/evidence/"
            "not-a-valid-object-id"
        ),
        headers=headers,
    )

    assert response.status_code == 404

    response = client.get(
        (
            "/api/v1/evidence/"
            "not-a-valid-object-id/"
            "download"
        ),
        headers=headers,
    )

    assert response.status_code == 404

    response = client.delete(
        (
            "/api/v1/evidence/"
            "not-a-valid-object-id"
        ),
        headers=headers,
    )

    assert response.status_code == 404