import uuid

from bson import ObjectId

from app.repositories.evidence_repository import (
    get_evidence,
)
from app.services import (
    evidence_storage_service,
)
from app.services.evidence_processing_service import (
    process_evidence_for_user,
)


def unique_email() -> str:
    return (
        f"evidence-processing-"
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
                "Evidence Processing User",

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

    return (
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )


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
                "processing.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_new_evidence_starts_pending(
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

    evidence = upload_text(
        client,
        token,
        b"Pending processing evidence.",
    )

    assert evidence[
        "processing_status"
    ] == "pending"

    assert evidence[
        "extraction_method"
    ] is None

    assert evidence[
        "extracted_character_count"
    ] == 0

    assert evidence[
        "processed_at"
    ] is None

    # Raw extracted content must never appear
    # in the ordinary API response.
    assert (
        "extracted_text"
        not in evidence
    )


def test_processing_persists_extracted_text_privately(
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

    content = (
        b"Invoice ABC-900\n"
        b"Amount paid: INR 42000"
    )

    evidence = upload_text(
        client,
        token,
        content,
    )

    evidence_id = evidence[
        "id"
    ]

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    async def process():
        return await process_evidence_for_user(
            evidence_id=evidence_id,
            user_id=user_id,
        )

    processed = client.portal.call(
        process
    )

    assert processed[
        "processing_status"
    ] == "ready"

    assert processed[
        "extraction_method"
    ] == "utf8_text"

    assert (
        "Invoice ABC-900"
        in processed[
            "extracted_text"
        ]
    )

    assert processed[
        "extracted_character_count"
    ] > 0

    assert processed[
        "processed_at"
    ] is not None

    # Public API should expose status but not text.
    response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence_id}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200

    public_data = response.json()

    assert public_data[
        "processing_status"
    ] == "ready"

    assert public_data[
        "extraction_method"
    ] == "utf8_text"

    assert (
        "extracted_text"
        not in public_data
    )


def test_processing_tampered_file_becomes_failed(
    client,
    monkeypatch,
    tmp_path,
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

    token = create_account_and_token(
        client
    )

    evidence = upload_text(
        client,
        token,
        b"Original evidence content.",
    )

    stored_files = [
        path
        for path in (
            upload_root
            / "evidence"
        ).rglob("*")
        if path.is_file()
    ]

    assert len(
        stored_files
    ) == 1

    stored_files[
        0
    ].write_bytes(
        b"Tampered evidence content."
    )

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    async def process():
        return await process_evidence_for_user(
            evidence_id=evidence[
                "id"
            ],
            user_id=user_id,
        )

    processed = client.portal.call(
        process
    )

    assert processed[
        "processing_status"
    ] == "failed"

    assert processed[
        "extracted_text"
    ] is None

    assert processed[
        "processing_error"
    ]

    response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 200

    public_data = response.json()

    assert public_data[
        "processing_status"
    ] == "failed"

    assert (
        "extracted_text"
        not in public_data
    )