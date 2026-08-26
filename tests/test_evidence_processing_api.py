import uuid
from pathlib import Path

from app.services import (
    evidence_storage_service,
)


def unique_email() -> str:
    return (
        f"evidence-process-api-"
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
                "Evidence Process API User",

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


def configure_storage(
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


def upload_text(
    client,
    token: str,
    content: bytes,
):
    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "process.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def upload_png(
    client,
    token: str,
):
    # Current upload validation checks the
    # required PNG signature.
    content = (
        b"\x89PNG\r\n\x1a\n"
        b"test-image-content"
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "image.png",
                content,
                "image/png",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_processing_endpoint_requires_authentication(
    client,
):
    response = client.post(
        (
            "/api/v1/evidence/"
            "000000000000000000000000/"
            "process"
        ),
        json={
            "retry":
                False
        },
    )

    assert response.status_code in (
        401,
        403,
    )


def test_text_evidence_can_be_processed(
    client,
    monkeypatch,
    tmp_path,
):
    configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    evidence = upload_text(
        client,
        token,
        (
            b"Invoice number API-100\n"
            b"Amount paid: INR 18000"
        ),
    )

    assert evidence[
        "processing_status"
    ] == "pending"

    response = client.post(
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

    assert response.status_code == 200, (
        response.text
    )

    processed = response.json()

    assert processed[
        "processing_status"
    ] == "ready"

    assert processed[
        "extraction_method"
    ] == "utf8_text"

    assert processed[
        "extracted_character_count"
    ] > 0

    assert processed[
        "processed_at"
    ] is not None

    # Raw extracted evidence must stay private.
    assert (
        "extracted_text"
        not in processed
    )


def test_processing_again_requires_explicit_retry(
    client,
    monkeypatch,
    tmp_path,
):
    configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    evidence = upload_text(
        client,
        token,
        b"Evidence retry test.",
    )

    process_url = (
        f"/api/v1/evidence/"
        f"{evidence['id']}/process"
    )

    first_response = client.post(
        process_url,
        headers=auth_headers(
            token
        ),
        json={
            "retry":
                False
        },
    )

    assert first_response.status_code == 200, (
        first_response.text
    )

    second_response = client.post(
        process_url,
        headers=auth_headers(
            token
        ),
        json={
            "retry":
                False
        },
    )

    assert second_response.status_code == 409, (
        second_response.text
    )

    assert (
        "retry=true"
        in second_response.text.lower()
    )

    retry_response = client.post(
        process_url,
        headers=auth_headers(
            token
        ),
        json={
            "retry":
                True
        },
    )

    assert retry_response.status_code == 200, (
        retry_response.text
    )

    assert retry_response.json()[
        "processing_status"
    ] == "ready"


def test_image_processing_returns_requires_ocr(
    client,
    monkeypatch,
    tmp_path,
):
    configure_storage(
        monkeypatch,
        tmp_path,
    )

    token = create_account_and_token(
        client
    )

    evidence = upload_png(
        client,
        token,
    )

    response = client.post(
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

    assert response.status_code == 200, (
        response.text
    )

    processed = response.json()

    assert processed[
        "processing_status"
    ] == "requires_ocr"

    assert processed[
        "extracted_character_count"
    ] == 0

    assert (
        "extracted_text"
        not in processed
    )


def test_other_user_cannot_process_evidence(
    client,
    monkeypatch,
    tmp_path,
):
    configure_storage(
        monkeypatch,
        tmp_path,
    )

    owner_token = create_account_and_token(
        client
    )

    other_token = create_account_and_token(
        client
    )

    evidence = upload_text(
        client,
        owner_token,
        b"Private owner evidence.",
    )

    response = client.post(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}/process"
        ),
        headers=auth_headers(
            other_token
        ),
        json={
            "retry":
                False
        },
    )

    # Do not reveal that another user's
    # evidence exists.
    assert response.status_code == 404


def test_tampered_file_processing_fails_closed(
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

    evidence = upload_text(
        client,
        token,
        b"Original evidence content.",
    )

    files = [
        path
        for path in (
            upload_root
            / "evidence"
        ).rglob("*")
        if path.is_file()
    ]

    assert len(
        files
    ) == 1

    files[
        0
    ].write_bytes(
        b"Tampered content."
    )

    response = client.post(
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

    assert response.status_code == 200, (
        response.text
    )

    processed = response.json()

    assert processed[
        "processing_status"
    ] == "failed"

    assert processed[
        "processing_error"
    ]

    assert processed[
        "extracted_character_count"
    ] == 0

    assert (
        "extracted_text"
        not in processed
    )