import uuid

from bson import ObjectId

from app.services import (
    evidence_storage_service,
)
from app.services.evidence_reconciliation_service import (
    build_evidence_health_report,
)


def unique_email() -> str:
    return (
        f"evidence-health-"
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


def create_account(
    client,
):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name":
                "Evidence Health User",

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


def upload_text(
    client,
    token,
    content: bytes,
):
    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(
            token
        ),
        files={
            "file": (
                "health.txt",
                content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, (
        response.text
    )

    return response.json()


def test_health_report_detects_missing_file(
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

    token = create_account(
        client
    )

    evidence = upload_text(
        client,
        token,
        b"Evidence that will disappear.",
    )

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    stored_paths = [
        path
        for path in (
            upload_root
            / "evidence"
        ).rglob("*")
        if path.is_file()
    ]

    assert len(
        stored_paths
    ) == 1

    # Simulate an evidence metadata record whose
    # physical artifact disappeared.
    stored_paths[
        0
    ].unlink()

    async def run_report():
        return await build_evidence_health_report(
            user_id=user_id,
            verify_hashes=True,
        )

    # IMPORTANT:
    # Run the coroutine on TestClient's portal.
    #
    # This is the same event-loop environment used by
    # FastAPI and the application's AsyncMongoClient.
    health = client.portal.call(
        run_report
    )

    assert health[
        "healthy"
    ] is False

    assert health[
        "issue_count"
    ] >= 1

    assert len(
        health[
            "missing_files"
        ]
    ) == 1

    assert (
        health[
            "missing_files"
        ][0][
            "evidence_id"
        ]
        == evidence[
            "id"
        ]
    )

    assert health[
        "missing_storage_paths"
    ] == []

    assert health[
        "unsafe_storage_paths"
    ] == []


def test_health_report_detects_orphan_file(
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

    token = create_account(
        client
    )

    evidence = upload_text(
        client,
        token,
        b"Healthy evidence.",
    )

    user_id = ObjectId(
        evidence[
            "user_id"
        ]
    )

    user_directory = (
        upload_root
        / "evidence"
        / evidence[
            "user_id"
        ]
    )

    assert user_directory.exists()

    orphan_path = (
        user_directory
        / "orphan-file.txt"
    )

    orphan_path.write_bytes(
        b"Unreferenced private file."
    )

    async def run_report():
        return await build_evidence_health_report(
            user_id=user_id,
            verify_hashes=False,
        )

    # Use FastAPI TestClient's existing async portal,
    # not anyio.run(), so MongoDB stays on the same
    # event loop.
    health = client.portal.call(
        run_report
    )

    assert health[
        "healthy"
    ] is False

    assert health[
        "issue_count"
    ] >= 1

    assert any(
        item[
            "storage_path"
        ].endswith(
            "orphan-file.txt"
        )
        for item in health[
            "orphan_files"
        ]
    )

    # The legitimate uploaded record itself should
    # remain healthy.
    assert any(
        item[
            "evidence_id"
        ]
        == evidence[
            "id"
        ]
        for item in health[
            "healthy_records"
        ]
    )