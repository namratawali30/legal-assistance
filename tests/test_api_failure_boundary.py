import uuid

from bson import ObjectId

import app.api.auth as auth_api
import app.api.chat as chat_api
import app.api.complaint_export as export_api

from app.services.complaint_export_service import (
    ComplaintExportGenerationError,
)


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_token(
    client,
) -> str:
    email = f"failure-boundary-" f"{uuid.uuid4().hex[:12]}" "@example.com"

    password = "TestPassword123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Failure Boundary User",
            "password": password,
        },
    )

    assert response.status_code == 201, response.text

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    token = data.get("access_token") or data.get("token")

    assert token

    return token


def test_unexpected_api_failure_is_generic(
    client,
    monkeypatch,
):
    token = create_token(client)

    async def fail_list(
        **kwargs,
    ):
        raise RuntimeError("mongodb://private-host:27017/" "secret-database-detail")

    monkeypatch.setattr(
        chat_api,
        "list_user_sessions",
        fail_list,
    )

    response = client.get(
        "/api/v1/chats",
        headers=auth_headers(token),
    )

    assert response.status_code == 500

    assert response.json() == {"detail": "Internal server error."}

    body = response.text

    assert "private-host" not in body
    assert "secret-database-detail" not in body

    assert response.headers["x-content-type-options"] == "nosniff"

    assert response.headers["cache-control"] == "no-store, private"

    assert response.headers["pragma"] == "no-cache"

    assert "Authorization" in response.headers.get(
        "vary",
        "",
    )


def test_expected_404_is_not_rewritten(
    client,
):
    token = create_token(client)

    response = client.get(
        "/api/v1/chats/not-a-valid-id",
        headers=auth_headers(token),
    )

    assert response.status_code == 404

    assert response.json()["detail"] == "Chat session not found"


def test_registration_valueerror_is_safe(
    client,
    monkeypatch,
):
    async def fail_register(
        **kwargs,
    ):
        raise ValueError("mongodb://secret-registration-host")

    monkeypatch.setattr(
        auth_api,
        "register_user",
        fail_register,
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "register-failure@example.com",
            "full_name": "Registration Failure",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 409

    assert "secret-registration-host" not in response.text


def test_login_valueerror_is_safe(
    client,
    monkeypatch,
):
    async def fail_login(
        **kwargs,
    ):
        raise ValueError("private authentication detail")

    monkeypatch.setattr(
        auth_api,
        "login_user",
        fail_login,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login-failure@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid email or password"

    assert "private authentication detail" not in response.text

    assert response.headers.get("www-authenticate") == "Bearer"


def test_pdf_export_failure_is_safe(
    client,
    monkeypatch,
):
    token = create_token(client)

    async def fail_export(
        **kwargs,
    ):
        raise ComplaintExportGenerationError("C:\\private\\reportlab-detail")

    monkeypatch.setattr(
        export_api,
        "export_complaint_pdf",
        fail_export,
    )

    response = client.get(
        ("/api/v1/complaints/" f"{ObjectId()}/export/pdf"),
        headers=auth_headers(token),
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": (
            "Complaint export could not be " "generated. Please try again later."
        )
    }

    assert "reportlab-detail" not in response.text


def test_docx_export_failure_is_safe(
    client,
    monkeypatch,
):
    token = create_token(client)

    async def fail_export(
        **kwargs,
    ):
        raise ComplaintExportGenerationError("C:\\private\\python-docx-detail")

    monkeypatch.setattr(
        export_api,
        "export_complaint_docx",
        fail_export,
    )

    response = client.get(
        ("/api/v1/complaints/" f"{ObjectId()}/export/docx"),
        headers=auth_headers(token),
    )

    assert response.status_code == 500

    assert "python-docx-detail" not in response.text
