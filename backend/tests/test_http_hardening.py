import uuid
import io
import zipfile

import pytest
from fastapi import Response
from bson import ObjectId
from app.services import evidence_storage_service


def test_health_endpoint_is_minimal(
    client,
):
    response = client.get("/health")

    assert response.status_code == 200

    assert response.json() == {"status": "ok"}

    body = response.text.lower()

    assert "mongodb" not in body
    assert "database" not in body
    assert "environment" not in body


def test_security_headers_are_added(
    client,
):
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"

    assert response.headers["x-frame-options"] == "DENY"

    assert response.headers["referrer-policy"] == "no-referrer"


def test_security_headers_exist_on_error_responses(
    client,
):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401

    assert response.headers["x-content-type-options"] == "nosniff"

    assert response.headers["x-frame-options"] == "DENY"


def test_unknown_route_returns_404_without_internal_details(
    client,
):
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404

    body = response.text.lower()

    forbidden = (
        "traceback",
        "mongodb://",
        "site-packages",
        "app/services/",
        "app\\services\\",
    )

    for value in forbidden:
        assert value not in body


# =========================================================
# HELPERS
# =========================================================


TEST_PASSWORD = "TestPassword123!"


def create_http_test_token(
    client,
) -> str:
    email = "http-hardening-" f"{uuid.uuid4().hex[:12]}" "@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "HTTP Hardening User",
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201, response.text

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =========================================================
# MALFORMED RESOURCE IDS
# =========================================================


@pytest.mark.parametrize(
    "bad_id",
    [
        "abc",
        "not-an-object-id",
        "z" * 24,
        "1234567890",
    ],
)
def test_malformed_chat_id_returns_404(
    client,
    bad_id,
):
    token = create_http_test_token(client)

    headers = auth_headers(token)

    response = client.get(
        f"/api/v1/chats/{bad_id}",
        headers=headers,
    )

    assert response.status_code == 404, response.text

    assert "traceback" not in (response.text.lower())


@pytest.mark.parametrize(
    "bad_id",
    [
        "abc",
        "not-an-object-id",
        "z" * 24,
        "1234567890",
    ],
)
def test_malformed_complaint_id_returns_404(
    client,
    bad_id,
):
    token = create_http_test_token(client)

    response = client.get(
        (f"/api/v1/complaints/" f"{bad_id}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text

    assert "traceback" not in (response.text.lower())


@pytest.mark.parametrize(
    "bad_id",
    [
        "abc",
        "not-an-object-id",
        "z" * 24,
        "1234567890",
    ],
)
def test_malformed_evidence_id_returns_404(
    client,
    bad_id,
):
    token = create_http_test_token(client)

    response = client.get(
        (f"/api/v1/evidence/" f"{bad_id}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text

    assert "traceback" not in (response.text.lower())


# =========================================================
# SAME BEHAVIOR FOR VALID BUT MISSING IDS
# =========================================================


@pytest.mark.parametrize(
    "path_template",
    [
        "/api/v1/chats/{id}",
        "/api/v1/complaints/{id}",
        "/api/v1/evidence/{id}",
    ],
)
def test_valid_but_missing_resource_id_returns_404(
    client,
    path_template,
):
    token = create_http_test_token(client)

    missing_id = str(ObjectId())

    response = client.get(
        path_template.format(id=missing_id),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text


# =========================================================
# MALFORMED IDS ON SECONDARY ROUTES
# =========================================================


def test_malformed_chat_id_on_messages_route_returns_404(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/chats/" "not-an-object-id/messages"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "extension",
    [
        "pdf",
        "docx",
    ],
)
def test_malformed_complaint_id_on_export_returns_404(
    client,
    extension,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/complaints/" "not-an-object-id/" f"export/{extension}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text


def test_malformed_evidence_id_on_download_returns_404(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/evidence/" "not-an-object-id/download"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text


# =========================================================
# DELETE PATHS MUST ALSO FAIL SAFELY
# =========================================================


@pytest.mark.parametrize(
    "path",
    [
        ("/api/v1/chats/" "not-an-object-id"),
        ("/api/v1/complaints/" "not-an-object-id"),
        ("/api/v1/evidence/" "not-an-object-id"),
    ],
)
def test_malformed_id_delete_returns_404(
    client,
    path,
):
    token = create_http_test_token(client)

    response = client.delete(
        path,
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text

    body = response.text.lower()

    assert "traceback" not in body
    assert "objectid" not in body
    assert "bson" not in body


# =========================================================
# REQUEST VALIDATION / PAYLOAD BOUNDARIES
# =========================================================


def test_registration_rejects_unknown_fields(
    client,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Request Validation User",
            "email": ("strict-register-" f"{uuid.uuid4().hex[:10]}" "@example.com"),
            "password": TEST_PASSWORD,
            # Client must never be able to submit
            # undeclared account-management fields.
            "role": "admin",
        },
    )

    assert response.status_code == 422, response.text


def test_login_rejects_unknown_fields(
    client,
):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": ("unknown-" f"{uuid.uuid4().hex[:10]}" "@example.com"),
            "password": TEST_PASSWORD,
            "unexpected": "value",
        },
    )

    assert response.status_code == 422, response.text


def test_registration_rejects_whitespace_only_name(
    client,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "     ",
            "email": ("blank-name-" f"{uuid.uuid4().hex[:10]}" "@example.com"),
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 422, response.text


def test_registration_rejects_oversized_full_name(
    client,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "A" * 101,
            "email": ("long-name-" f"{uuid.uuid4().hex[:10]}" "@example.com"),
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_oversized_title(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "T" * 201,
            "category": "consumer_rights",
            "complainant_name": "Validation User",
            "respondent_name": "ABC Seller",
            "facts": (
                "This is a sufficiently detailed "
                "test complaint describing the "
                "consumer dispute."
            ),
        },
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_oversized_facts(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Payload boundary test",
            "category": "consumer_rights",
            "complainant_name": "Validation User",
            "respondent_name": "ABC Seller",
            "facts": "F" * 15001,
        },
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_invalid_category(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Invalid category test",
            "category": "made_up_legal_category",
            "complainant_name": "Validation User",
            "respondent_name": "ABC Seller",
            "facts": (
                "This complaint contains enough "
                "text to satisfy the minimum "
                "facts requirement."
            ),
        },
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_invalid_incident_date(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Invalid date test",
            "category": "consumer_rights",
            "complainant_name": "Validation User",
            "respondent_name": "ABC Seller",
            "incident_date": "definitely-not-a-date",
            "facts": (
                "This complaint contains enough "
                "text to satisfy the minimum "
                "facts requirement."
            ),
        },
    )

    assert response.status_code == 422, response.text


def test_evidence_upload_rejects_oversized_title(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data={
            "title": "T" * 201,
        },
        files={
            "file": (
                "boundary.txt",
                b"test evidence",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422, response.text


def test_evidence_upload_rejects_oversized_description(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data={
            "description": "D" * 2001,
        },
        files={
            "file": (
                "boundary.txt",
                b"test evidence",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422, response.text


# =========================================================
# STRICT CHAT REQUESTS
# =========================================================


def test_chat_rejects_unknown_fields(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(token),
        json={
            "title": "Valid title",
            "category": "consumer_rights",
            "user_id": str(ObjectId()),
        },
    )

    assert response.status_code == 422, response.text


def test_chat_rejects_whitespace_only_title(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(token),
        json={
            "title": "       ",
            "category": "consumer_rights",
        },
    )

    assert response.status_code == 422, response.text


def test_chat_message_rejects_whitespace_only_content(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/chats/" f"{ObjectId()}/messages"),
        headers=auth_headers(token),
        json={"content": "      "},
    )

    assert response.status_code == 422, response.text


def test_chat_message_rejects_oversized_content(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/chats/" f"{ObjectId()}/messages"),
        headers=auth_headers(token),
        json={"content": "A" * 10001},
    )

    assert response.status_code == 422, response.text


def test_chat_message_rejects_control_characters(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/chats/" f"{ObjectId()}/messages"),
        headers=auth_headers(token),
        json={"content": "Valid text\x00hidden"},
    )

    assert response.status_code == 422, response.text


# =========================================================
# STRICT COMPLAINT REQUESTS
# =========================================================


def valid_complaint_payload():
    return {
        "title": "Request validation complaint",
        "category": "consumer_rights",
        "complainant_name": "Validation User",
        "respondent_name": "ABC Seller",
        "facts": (
            "This complaint contains enough "
            "factual information for request "
            "validation testing."
        ),
        "additional_details": {},
    }


def test_complaint_rejects_unknown_fields(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["status"] = "finalized"

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_whitespace_only_required_text(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["complainant_name"] = "      "

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_oversized_additional_details(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["additional_details"] = {"large_value": "X" * 40000}

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_deeply_nested_additional_details(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["additional_details"] = {
        "a": {"b": {"c": {"d": {"e": {"f": {"g": "too deep"}}}}}}
    }

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_complaint_rejects_too_many_additional_detail_items(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["additional_details"] = {f"key_{index}": index for index in range(101)}

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_generated_text_rejects_oversized_body(
    client,
):
    token = create_http_test_token(client)

    response = client.patch(
        ("/api/v1/complaints/" f"{ObjectId()}/generated-text"),
        headers=auth_headers(token),
        json={"generated_text": "X" * 30001},
    )

    assert response.status_code == 422, response.text


def test_generate_rejects_string_boolean(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/complaints/" f"{ObjectId()}/generate"),
        headers=auth_headers(token),
        json={"regenerate": "true"},
    )

    assert response.status_code == 422, response.text


def test_finalize_rejects_string_boolean(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/complaints/" f"{ObjectId()}/finalize"),
        headers=auth_headers(token),
        json={"confirm": "true"},
    )

    assert response.status_code == 422, response.text


# =========================================================
# STRICT EVIDENCE REQUESTS
# =========================================================


def test_evidence_update_rejects_unknown_fields(
    client,
):
    token = create_http_test_token(client)

    response = client.patch(
        ("/api/v1/evidence/" f"{ObjectId()}"),
        headers=auth_headers(token),
        json={
            "title": "Valid title",
            "status": "deleted",
        },
    )

    assert response.status_code == 422, response.text


def test_evidence_update_rejects_whitespace_title(
    client,
):
    token = create_http_test_token(client)

    response = client.patch(
        ("/api/v1/evidence/" f"{ObjectId()}"),
        headers=auth_headers(token),
        json={"title": "       "},
    )

    assert response.status_code == 422, response.text


def test_evidence_update_rejects_oversized_description(
    client,
):
    token = create_http_test_token(client)

    response = client.patch(
        ("/api/v1/evidence/" f"{ObjectId()}"),
        headers=auth_headers(token),
        json={"description": "D" * 2001},
    )

    assert response.status_code == 422, response.text


def test_evidence_process_rejects_string_boolean(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/evidence/" f"{ObjectId()}/process"),
        headers=auth_headers(token),
        json={"retry": "true"},
    )

    assert response.status_code == 422, response.text


# =========================================================
# RESPONSE / CACHE / SECURITY HEADERS
# =========================================================


def assert_private_api_headers(
    response,
):
    cache_control = response.headers.get("cache-control", "").lower()

    assert "no-store" in (cache_control)

    assert "private" in (cache_control)

    assert response.headers.get("pragma") == "no-cache"

    assert response.headers.get("x-content-type-options") == "nosniff"

    assert response.headers.get("x-frame-options") == "DENY"

    assert response.headers.get("referrer-policy") == "no-referrer"

    assert response.headers.get("x-permitted-cross-domain-policies") == "none"

    vary = {
        item.strip().lower()
        for item in (response.headers.get("vary", "").split(","))
        if item.strip()
    }

    assert "authorization" in vary


def test_authenticated_json_response_is_not_cacheable(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    assert_private_api_headers(response)


def test_authentication_error_is_not_cacheable(
    client,
):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401

    assert_private_api_headers(response)


def test_validation_error_is_not_cacheable(
    client,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "full_name": "Validation User",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 422

    assert_private_api_headers(response)


def test_chat_list_response_is_not_cacheable(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/chats",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    assert_private_api_headers(response)


def test_complaint_list_response_is_not_cacheable(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/complaints",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    assert_private_api_headers(response)


def test_evidence_list_response_is_not_cacheable(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    assert_private_api_headers(response)


def test_health_endpoint_does_not_expose_private_api_cache_policy(
    client,
):
    response = client.get("/health")

    assert response.status_code == 200

    # Health still receives general security headers.
    assert response.headers.get("x-content-type-options") == "nosniff"

    assert response.headers.get("x-frame-options") == "DENY"

    # But it is not treated as a private user API.
    assert "authorization" not in {
        item.strip().lower()
        for item in (response.headers.get("vary", "").split(","))
        if item.strip()
    }


def test_existing_cache_control_is_not_overwritten(
    client,
):
    from app.main import app

    test_path = "/api/v1/" "_header-preservation-test"

    async def temporary_endpoint():
        return Response(
            content="ok",
            media_type="text/plain",
            headers={
                "Cache-Control": ("no-store, no-cache, " "must-revalidate, private"),
                "Pragma": "no-cache",
            },
        )

    app.add_api_route(
        test_path,
        temporary_endpoint,
        methods=["GET"],
    )

    try:
        response = client.get(test_path)

        assert response.status_code == 200

        assert response.headers["cache-control"] == (
            "no-store, no-cache, " "must-revalidate, private"
        )

    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(
                route,
                "path",
                None,
            )
            != test_path
        ]


def test_export_filename_header_is_sanitized():
    from app.api.complaint_export import (
        build_download_headers,
    )

    headers = build_download_headers('complaint"\r\n' "X-Evil: injected.pdf")

    disposition = headers["Content-Disposition"]

    assert "\r" not in disposition
    assert "\n" not in disposition

    assert "X-Evil:" in disposition

    # It remains filename text; it must not become
    # a second HTTP header.
    assert disposition.startswith("attachment; filename=")

    assert "no-store" in headers["Cache-Control"]


# =========================================================
# ERROR STATUS CONSISTENCY
# =========================================================


def test_generation_conflict_returns_409(
    client,
    monkeypatch,
):
    from app.services.complaint_generation_service import (
        ComplaintGenerationConflictError,
    )

    async def fail_generation(
        *args,
        **kwargs,
    ):
        raise ComplaintGenerationConflictError("Complaint changed during generation.")

    monkeypatch.setattr(
        "app.api.complaint." "generate_complaint_for_user",
        fail_generation,
    )

    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/complaints/" f"{ObjectId()}/generate"),
        headers=auth_headers(token),
        json={"regenerate": False},
    )

    assert response.status_code == 409, response.text


def test_finalize_concurrent_update_returns_409(
    client,
    monkeypatch,
):
    from app.services.complaint_service import (
        ComplaintConcurrentUpdateError,
    )

    async def fail_finalize(
        *args,
        **kwargs,
    ):
        raise ComplaintConcurrentUpdateError("Complaint changed.")

    monkeypatch.setattr(
        "app.api.complaint." "finalize_complaint",
        fail_finalize,
    )

    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/complaints/" f"{ObjectId()}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )

    assert response.status_code == 409, response.text


def test_llm_unavailable_returns_safe_503(
    client,
    monkeypatch,
):
    from app.services.complaint_generation_service import (
        ComplaintLLMUnavailableError,
    )

    async def fail_generation(
        *args,
        **kwargs,
    ):
        raise ComplaintLLMUnavailableError(
            "Provider failed with secret=" "super-sensitive-value"
        )

    monkeypatch.setattr(
        "app.api.complaint." "generate_complaint_for_user",
        fail_generation,
    )

    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/complaints/" f"{ObjectId()}/generate"),
        headers=auth_headers(token),
        json={"regenerate": False},
    )

    assert response.status_code == 503, response.text

    body = response.text.lower()

    assert "super-sensitive-value" not in body

    assert "provider failed" not in body


def test_evidence_persistence_failure_returns_safe_500(
    client,
    monkeypatch,
):
    from app.services.evidence_service import (
        EvidencePersistenceError,
    )

    async def fail_upload(
        *args,
        **kwargs,
    ):
        raise EvidencePersistenceError(
            "C:\\secret\\internal\\path " "mongodb internal details"
        )

    monkeypatch.setattr(
        "app.api.evidence." "create_evidence_for_user",
        fail_upload,
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "test.txt",
                b"test evidence",
                "text/plain",
            )
        },
    )

    assert response.status_code == 500, response.text

    body = response.text.lower()

    assert "secret" not in body
    assert "mongodb" not in body
    assert "internal\\path" not in body


def test_evidence_processing_failure_returns_safe_500(
    client,
    monkeypatch,
):
    import app.services.evidence_processing_service as processing_service

    async def fail_processing(
        *args,
        **kwargs,
    ):
        raise (
            processing_service.EvidenceProcessingError(
                "parser crashed at " "C:\\private\\file.pdf"
            )
        )

    monkeypatch.setattr(
        processing_service,
        "process_evidence_for_user",
        fail_processing,
    )

    token = create_http_test_token(client)

    response = client.post(
        ("/api/v1/evidence/" f"{ObjectId()}/process"),
        headers=auth_headers(token),
        json={"retry": False},
    )

    assert response.status_code == 500, response.text

    body = response.text.lower()

    assert "private" not in body
    assert "parser crashed" not in body


def test_evidence_delete_failure_returns_safe_500(
    client,
    monkeypatch,
):
    from app.services.evidence_service import (
        EvidenceDeleteError,
    )

    async def fail_delete(
        *args,
        **kwargs,
    ):
        raise EvidenceDeleteError("Failed deleting " "C:\\secret\\evidence.txt")

    monkeypatch.setattr(
        "app.api.evidence." "remove_evidence",
        fail_delete,
    )

    token = create_http_test_token(client)

    response = client.delete(
        ("/api/v1/evidence/" f"{ObjectId()}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 500, response.text

    body = response.text.lower()

    assert "secret" not in body
    assert "evidence.txt" not in body


# =========================================================
# INPUT ABUSE RESISTANCE
# =========================================================


def test_extremely_long_chat_id_fails_safely(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/chats/" + ("A" * 10000)),
        headers=auth_headers(token),
    )

    assert response.status_code in {
        404,
        414,
    }

    body = response.text.lower()

    assert "traceback" not in body
    assert "bson" not in body
    assert "objectid" not in body


def test_extremely_long_complaint_id_fails_safely(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/complaints/" + ("A" * 10000)),
        headers=auth_headers(token),
    )

    assert response.status_code in {
        404,
        414,
    }

    assert "traceback" not in (response.text.lower())


def test_extremely_long_evidence_id_fails_safely(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        ("/api/v1/evidence/" + ("A" * 10000)),
        headers=auth_headers(token),
    )

    assert response.status_code in {
        404,
        414,
    }

    assert "traceback" not in (response.text.lower())


def test_evidence_list_handles_blank_complaint_filter(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/evidence",
        params={"complaint_id": "     "},
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text


def test_evidence_list_malformed_complaint_filter_fails_safely(
    client,
):
    token = create_http_test_token(client)

    response = client.get(
        "/api/v1/evidence",
        params={"complaint_id": "not-an-object-id"},
        headers=auth_headers(token),
    )

    assert response.status_code == 404, response.text

    body = response.text.lower()

    assert "traceback" not in body
    assert "bson" not in body


def test_chat_title_rejects_null_byte(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(token),
        json={
            "title": "Normal\x00Hidden",
            "category": "consumer_rights",
        },
    )

    assert response.status_code == 422, response.text


def test_complaint_facts_reject_null_byte(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["facts"] = (
        "This complaint initially looks valid "
        "but contains a hidden\x00control value."
    )

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_additional_details_reject_control_characters(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["additional_details"] = {"note": "visible\x00hidden"}

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_additional_details_rejects_extreme_list_size(
    client,
):
    token = create_http_test_token(client)

    payload = valid_complaint_payload()

    payload["additional_details"] = {"items": list(range(101))}

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_evidence_title_rejects_control_character(
    client,
):
    token = create_http_test_token(client)

    response = client.patch(
        ("/api/v1/evidence/" f"{ObjectId()}"),
        headers=auth_headers(token),
        json={"title": "Invoice\x00Hidden"},
    )

    assert response.status_code == 422, response.text


def test_invalid_legal_categories_are_rejected_everywhere(
    client,
):
    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/chats",
        headers=auth_headers(token),
        json={
            "title": "Invalid category",
            "category": "cybercrime",
        },
    )

    assert response.status_code == 422

    payload = valid_complaint_payload()

    payload["category"] = "cybercrime"

    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json=payload,
    )

    assert response.status_code == 422


# =========================================================
# UPLOAD ABUSE RESISTANCE
# =========================================================


def test_oversized_evidence_upload_returns_413(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    # Keep the test small rather than allocating the
    # normal production maximum.
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "max_upload_size_mb",
        1,
    )

    token = create_http_test_token(client)

    oversized = b"A" * ((1024 * 1024) + 1)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "too-large.txt",
                oversized,
                "text/plain",
            )
        },
    )

    assert response.status_code == 413, response.text

    # Rejected uploads must not leave a successful
    # evidence record behind.
    response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_unsupported_evidence_extension_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "payload.exe",
                b"MZ fake executable",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400, response.text


def test_double_extension_does_not_bypass_validation(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "invoice.pdf.exe",
                b"MZ fake executable",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400, response.text


def test_fake_pdf_signature_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "fake.pdf",
                (b"This is not actually " b"a PDF document."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400, response.text

def test_declared_pdf_mime_for_text_file_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "invoice.txt",
                b"ordinary invoice text",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400, response.text


def build_malicious_docx_with_traversal() -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0"?>'
                '<Types xmlns="http://schemas.'
                "openxmlformats.org/package/"
                '2006/content-types"></Types>'
            ),
        )

        archive.writestr(
            "word/document.xml",
            ('<?xml version="1.0"?>' "<document></document>"),
        )

        # ZIP path traversal entry.
        archive.writestr(
            "../outside.txt",
            "must never be extracted",
        )

    return buffer.getvalue()


def test_docx_zip_path_traversal_is_rejected(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    payload = build_malicious_docx_with_traversal()

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "malicious.docx",
                payload,
                (
                    "application/vnd."
                    "openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )
        },
    )

    assert response.status_code == 400, response.text

    assert not (tmp_path / "outside.txt").exists()


def test_path_like_upload_filename_cannot_escape_storage(
    client,
    monkeypatch,
    tmp_path,
):
    upload_root = tmp_path / "uploads"

    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(upload_root),
    )

    token = create_http_test_token(client)

    outside_target = tmp_path / "escape.txt"

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "../../escape.txt",
                b"safe text evidence",
                "text/plain",
            )
        },
    )

    # Either rejecting the suspicious name or safely
    # normalizing it is acceptable. Escaping the upload
    # root is never acceptable.
    assert response.status_code in {
        201,
        400,
    }, response.text

    assert not outside_target.exists()


def test_failed_upload_does_not_create_visible_evidence_record(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_http_test_token(client)

    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        files={
            "file": (
                "malware.exe",
                b"MZ",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400

    response = client.get(
        "/api/v1/evidence",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == []
