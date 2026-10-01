import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from bson import ObjectId
from fastapi import HTTPException
from jose import jwt

from app.config import settings
from app.core.dependencies import (
    require_role,
)
from app.repositories.user_repository import (
    users_collection,
)
from app.services import (
    evidence_storage_service,
)

# =========================================================
# HELPERS
# =========================================================


PASSWORD = "TestPassword123!"


def unique_email(
    prefix: str = "security",
) -> str:
    return f"{prefix}-" f"{uuid.uuid4().hex[:12]}" "@example.com"


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_account(
    client,
    *,
    email: str | None = None,
    password: str = PASSWORD,
):
    email = email or unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Security Test User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201, response.text

    return {
        "email": email,
        "password": password,
        "user": response.json(),
    }


def login_account(
    client,
    email: str,
    password: str = PASSWORD,
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    token = response.json().get("access_token")

    assert token

    return token


def create_account_and_token(
    client,
):
    account = register_account(client)

    token = login_account(
        client,
        account["email"],
        account["password"],
    )

    return (
        account,
        token,
    )


def create_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Security boundary complaint",
            "category": "consumer_rights",
            "complainant_name": "Security Test User",
            "complainant_address": "Test Address",
            "complainant_contact": "9999999999",
            "respondent_name": "ABC Seller",
            "respondent_address": "Seller Address",
            "incident_date": "2026-08-01",
            "incident_location": "Test City",
            "facts": (
                "I purchased a defective product "
                "and the seller refused to provide "
                "a refund."
            ),
            "relief_requested": "Refund of the purchase amount.",
            "additional_details": {},
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def upload_evidence(
    client,
    token: str,
    complaint_id: str | None = None,
):
    data = {
        "title": "Security test invoice",
    }

    if complaint_id is not None:
        data["complaint_id"] = complaint_id

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data=data,
        files={
            "file": (
                "security-invoice.txt",
                (b"Invoice SECURITY-001\n" b"Amount paid: INR 25,000"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


# =========================================================
# AUTHENTICATION BOUNDARY
# =========================================================


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/me",
        "/api/v1/complaints",
        "/api/v1/evidence",
    ],
)
def test_protected_routes_require_bearer_token(
    client,
    path,
):
    response = client.get(path)

    assert response.status_code == 401, response.text

    assert response.headers.get("www-authenticate") == "Bearer"


def test_malformed_bearer_token_returns_401(
    client,
):
    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers("this-is-not-a-valid-jwt"),
    )

    assert response.status_code == 401, response.text

    assert response.headers.get("www-authenticate") == "Bearer"


def test_wrong_signature_token_returns_401(
    client,
):
    now = datetime.now(timezone.utc)

    forged = jwt.encode(
        {
            "sub": str(ObjectId()),
            "role": "admin",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        "x" * 64,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(forged),
    )

    assert response.status_code == 401, response.text


def test_expired_token_returns_401(
    client,
):
    now = datetime.now(timezone.utc)

    expired = jwt.encode(
        {
            "sub": str(ObjectId()),
            "role": "user",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=(settings.jwt_algorithm),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(expired),
    )

    assert response.status_code == 401, response.text


def test_valid_token_for_missing_user_returns_401(
    client,
):
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": str(ObjectId()),
            "role": "admin",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.jwt_secret,
        algorithm=(settings.jwt_algorithm),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 401, response.text

    # Do not disclose whether the account exists.
    assert "user not found" not in (response.text.lower())


def test_inactive_user_token_is_rejected(
    client,
):
    account, token = create_account_and_token(client)

    user_id = ObjectId(account["user"]["id"])

    async def deactivate():
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {"is_active": False}},
        )

    client.portal.call(deactivate)

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 401, response.text

    assert "inactive" not in (response.text.lower())


# =========================================================
# AUTH RESPONSE PRIVACY
# =========================================================


def test_register_response_never_exposes_password_fields(
    client,
):
    account = register_account(client)

    body = account["user"]

    forbidden = {
        "password",
        "password_hash",
        "hashed_password",
    }

    assert forbidden.isdisjoint(body.keys())


def test_me_response_never_exposes_password_fields(
    client,
):
    account, token = create_account_and_token(client)

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    body = response.json()

    forbidden = {
        "password",
        "password_hash",
        "hashed_password",
    }

    assert forbidden.isdisjoint(body.keys())

    assert body["id"] == account["user"]["id"]


# =========================================================
# EMAIL CANONICALIZATION
# =========================================================


def test_email_registration_is_case_insensitive(
    client,
):
    suffix = uuid.uuid4().hex[:12]

    mixed_case = f"Security-{suffix}" "@Example.COM"

    first = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Case Test User",
            "email": mixed_case,
            "password": PASSWORD,
        },
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate Case User",
            "email": mixed_case.lower(),
            "password": PASSWORD,
        },
    )

    assert second.status_code == 409, second.text


def test_login_email_is_case_insensitive(
    client,
):
    email = unique_email("case-login")

    register_account(
        client,
        email=email,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email.upper(),
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text


# =========================================================
# PASSWORD BOUNDARY
# =========================================================


def test_password_over_72_utf8_bytes_is_rejected(
    client,
):
    # 40 emoji are only 40 Python characters but
    # substantially more than 72 UTF-8 bytes.
    oversized_password = "🔐" * 40

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Password Boundary User",
            "email": unique_email("password-bytes"),
            "password": oversized_password,
        },
    )

    assert response.status_code == 422, response.text


# =========================================================
# ROLE AUTHORIZATION PRIMITIVE
# =========================================================


def test_require_role_rejects_wrong_database_role(
    client,
):
    checker = require_role("admin")

    async def run():
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user={"role": "user"})

        return exc_info.value

    exc = client.portal.call(run)

    assert exc.status_code == 403


def test_require_role_accepts_required_role(
    client,
):
    checker = require_role("admin")

    current_user = {"role": "admin"}

    async def run():
        return await checker(current_user=current_user)

    result = client.portal.call(run)

    assert result is current_user


# =========================================================
# CROSS-USER COMPLAINT ISOLATION
# =========================================================


def test_other_user_cannot_read_modify_or_delete_complaint(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        owner_token,
    )

    complaint_url = f"/api/v1/complaints/" f"{complaint['id']}"

    response = client.get(
        complaint_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    response = client.patch(
        complaint_url,
        headers=auth_headers(attacker_token),
        json={"incident_location": "Unauthorized Location"},
    )

    assert response.status_code == 404, response.text

    response = client.delete(
        complaint_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    # Owner's complaint must still exist unchanged.
    response = client.get(
        complaint_url,
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200, response.text

    assert response.json()["incident_location"] == "Test City"


def test_other_user_complaint_list_does_not_leak_owner_records(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        owner_token,
    )

    response = client.get(
        "/api/v1/complaints",
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 200, response.text

    ids = {item["id"] for item in response.json()}

    assert complaint["id"] not in ids


# =========================================================
# CROSS-USER EVIDENCE ISOLATION
# =========================================================


def test_other_user_cannot_attach_evidence_to_foreign_complaint(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        owner_token,
    )

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(attacker_token),
        data={
            "complaint_id": complaint["id"],
            "title": "Unauthorized evidence",
        },
        files={
            "file": (
                "unauthorized.txt",
                b"must not be attached",
                "text/plain",
            )
        },
    )

    # Ownership failure is deliberately indistinguishable
    # from a missing complaint.
    assert response.status_code == 404, response.text


def test_other_user_cannot_access_evidence(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    evidence = upload_evidence(
        client,
        owner_token,
    )

    evidence_url = f"/api/v1/evidence/" f"{evidence['id']}"

    response = client.get(
        evidence_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    response = client.get(
        (f"{evidence_url}" "/download"),
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    response = client.patch(
        evidence_url,
        headers=auth_headers(attacker_token),
        json={"title": "Unauthorized edit"},
    )

    assert response.status_code == 404, response.text

    response = client.delete(
        evidence_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    # Owner must still retain the evidence.
    response = client.get(
        evidence_url,
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200, response.text


def test_other_user_evidence_list_does_not_leak_owner_records(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    evidence = upload_evidence(
        client,
        owner_token,
    )

    response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 200, response.text

    ids = {item["id"] for item in response.json()}

    assert evidence["id"] not in ids


# =========================================================
# INTERNAL FIELD LEAKAGE
# =========================================================


def test_evidence_response_does_not_expose_private_fields(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    _account, token = create_account_and_token(client)

    evidence = upload_evidence(
        client,
        token,
    )

    forbidden = {
        "storage_path",
        "stored_filename",
        "extracted_text",
        "lifecycle_lock_token",
        "lifecycle_lock_operation",
        "lifecycle_lock_acquired_at",
        "lifecycle_lock_expires_at",
    }

    assert forbidden.isdisjoint(evidence.keys())


def test_complaint_response_does_not_expose_internal_fields(
    client,
):
    _account, token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        token,
    )

    forbidden = {
        "revision",
        "lifecycle_lock_token",
        "lifecycle_lock_operation",
        "lifecycle_lock_acquired_at",
        "lifecycle_lock_expires_at",
    }

    assert forbidden.isdisjoint(complaint.keys())


# =========================================================
# CHAT SECURITY BOUNDARY
# =========================================================


def create_chat(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(token),
        json={
            "title": "Security boundary chat",
            "category": "consumer_rights",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def test_chat_routes_require_authentication(
    client,
):
    response = client.get("/api/v1/chats")

    assert response.status_code == 401, response.text

    assert response.headers.get("www-authenticate") == "Bearer"


def test_other_user_cannot_read_modify_or_delete_chat(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    chat = create_chat(
        client,
        owner_token,
    )

    chat_url = f"/api/v1/chats/" f"{chat['id']}"

    response = client.get(
        chat_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    response = client.patch(
        chat_url,
        headers=auth_headers(attacker_token),
        json={"title": "Unauthorized title"},
    )

    assert response.status_code == 404, response.text

    response = client.delete(
        chat_url,
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    # Owner must still retain the chat.
    response = client.get(
        chat_url,
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200, response.text

    assert response.json()["title"] == "Security boundary chat"


def test_other_user_cannot_access_foreign_chat_messages(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    chat = create_chat(
        client,
        owner_token,
    )

    session_id = chat["id"]

    response = client.get(
        (f"/api/v1/chats/" f"{session_id}/messages"),
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text

    # This must fail before any LLM call because the
    # attacker does not own the session.
    response = client.post(
        (f"/api/v1/chats/" f"{session_id}/messages"),
        headers=auth_headers(attacker_token),
        json={"content": "This message must not be accepted."},
    )

    assert response.status_code == 404, response.text


def test_other_user_chat_list_does_not_leak_owner_sessions(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    chat = create_chat(
        client,
        owner_token,
    )

    response = client.get(
        "/api/v1/chats",
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 200, response.text

    ids = {item["id"] for item in response.json()}

    assert chat["id"] not in ids


def test_other_user_cannot_retry_message_in_foreign_chat(
    client,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    chat = create_chat(
        client,
        owner_token,
    )

    response = client.post(
        (f"/api/v1/chats/" f"{chat['id']}/messages/" f"{ObjectId()}/retry"),
        headers=auth_headers(attacker_token),
    )

    assert response.status_code == 404, response.text


# =========================================================
# COMPLAINT EXPORT SECURITY BOUNDARY
# =========================================================


@pytest.mark.parametrize(
    "extension",
    [
        "pdf",
        "docx",
    ],
)
def test_complaint_exports_require_authentication(
    client,
    extension,
):
    response = client.get(
        (f"/api/v1/complaints/" f"{ObjectId()}/export/" f"{extension}")
    )

    assert response.status_code == 401, response.text


@pytest.mark.parametrize(
    "extension",
    [
        "pdf",
        "docx",
    ],
)
def test_other_user_cannot_export_foreign_complaint(
    client,
    extension,
):
    _owner, owner_token = create_account_and_token(client)

    _attacker, attacker_token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        owner_token,
    )

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}/export/" f"{extension}"),
        headers=auth_headers(attacker_token),
    )

    # Critical information-hiding property:
    # another user's complaint must look nonexistent,
    # not merely "not finalized".
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "extension",
    [
        "pdf",
        "docx",
    ],
)
def test_owner_draft_export_is_rejected_as_not_finalized(
    client,
    extension,
):
    _owner, owner_token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        owner_token,
    )

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}/export/" f"{extension}"),
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 409, response.text
