import uuid
from pathlib import Path

from pymongo.errors import DuplicateKeyError

from app.services import evidence_storage_service


def unique_email() -> str:
    return (
        f"evidence-race-"
        f"{uuid.uuid4().hex[:10]}"
        "@example.com"
    )


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}"
    }


def create_account_and_token(
    client,
) -> str:
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Evidence Race Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert register_response.status_code in (
        200,
        201,
    ), register_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200, (
        login_response.text
    )

    data = login_response.json()

    token = (
        data.get("access_token")
        or data.get("token")
    )

    assert token

    return token


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


def test_duplicate_key_race_cleans_redundant_file(
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

    # Simulate the application-level duplicate
    # lookup finding no existing record.
    async def no_duplicate(
        user_id,
        sha256,
        complaint_id=None,
    ):
        return None

    monkeypatch.setattr(
        (
            "app.services."
            "evidence_service."
            "find_duplicate_evidence"
        ),
        no_duplicate,
    )

    # Simulate the MongoDB unique index rejecting
    # the insert because another concurrent request
    # inserted the same evidence first.
    async def duplicate_key_insert(
        evidence_data,
    ):
        raise DuplicateKeyError(
            "simulated duplicate-key race"
        )

    monkeypatch.setattr(
        (
            "app.services."
            "evidence_service."
            "create_evidence"
        ),
        duplicate_key_insert,
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        data={
            "title": "Concurrent evidence",
            "description": (
                "Race-condition simulation"
            ),
        },
        files={
            "file": (
                "race.txt",
                (
                    b"Evidence content used to "
                    b"simulate a duplicate-key race."
                ),
                "text/plain",
            )
        },
    )

    assert response.status_code == 409, (
        response.text
    )

    assert (
        "already been uploaded"
        in response.text.lower()
    )

    # The physical file was created before
    # MongoDB rejected the insert.
    #
    # It must be cleaned up after DuplicateKeyError.
    assert stored_files(
        upload_root
    ) == []