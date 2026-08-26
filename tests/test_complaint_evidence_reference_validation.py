import uuid

from bson import ObjectId

from app.repositories.complaint_repository import (
    update_complaint,
)


def unique_email() -> str:
    return f"complaint-evidence-ref-" f"{uuid.uuid4().hex[:10]}" "@example.com"


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_account_and_token(
    client,
) -> str:
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Evidence Reference Test User",
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

    assert login_response.status_code == 200, login_response.text

    data = login_response.json()

    token = data.get("access_token") or data.get("token")

    assert token

    return token


def create_draft_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Evidence-backed consumer complaint",
            "category": "consumer_rights",
            "complainant_name": "Evidence Reference User",
            "complainant_address": "Test Address",
            "complainant_contact": "9999999999",
            "respondent_name": "ABC Electronics",
            "respondent_address": "Seller Address",
            "incident_date": "2026-08-01",
            "incident_location": "Test City",
            "facts": (
                "I purchased a defective mobile phone "
                "from the respondent and requested a "
                "refund after discovering the defect."
            ),
            "relief_requested": "Refund of the purchase amount.",
            "additional_details": {
                "invoice_number": "EVIDENCE-TEST-001",
            },
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def fake_generation_result_with_evidence():
    return {
        "generated": True,
        "reason": "success",
        "generated_text": (
            "To,\n"
            "[Appropriate Authority]\n\n"
            "Subject: Consumer complaint\n\n"
            "Respected Sir/Madam,\n\n"
            "The uploaded invoice records a purchase "
            "amount of INR 25,000. [EVIDENCE_1]\n\n"
            "The relevant statutory complaint "
            "provisions provide the legal basis for "
            "this complaint. [SOURCE_1]\n\n"
            "I request appropriate relief.\n\n"
            "Drafting note: This AI-generated draft "
            "is for general informational assistance "
            "and should be reviewed before submission."
        ),
        "sources": [
            {
                "citation_id": "SOURCE_1",
                "title": "Consumer Protection Act, 2019",
                "authority": "India Code",
                "category": "consumer_rights",
                "provision_type": "section",
                "provision_number": "35",
                "provision_title": "Manner in which complaint shall be made",
                "page_start": 20,
                "page_end": 21,
                "landing_page": "https://www.indiacode.nic.in/",
                "pdf_url": ("https://www.indiacode.nic.in/" "example.pdf"),
            }
        ],
        "evidence_references": [
            {
                "citation_id": "EVIDENCE_1",
                "evidence_id": str(ObjectId()),
                "complaint_id": None,
                "title": "Purchase invoice",
                "original_filename": "invoice.txt",
                "evidence_type": "text",
                "media_type": "text/plain",
                "sha256": "a" * 64,
                "extraction_method": "utf8_text",
                "extracted_page_count": None,
                "included_characters": 54,
                "truncated": False,
            }
        ],
        "confidence": {
            "accepted": True,
            "reason": "sufficient_relevance",
            "top_score": 0.63,
            "threshold": 0.52,
        },
        "citation_validation": {
            "valid": True,
            "found": ["SOURCE_1"],
            "valid_citations": ["SOURCE_1"],
            "invalid_citations": [],
        },
        "evidence_citation_validation": {
            "valid": True,
            "found": ["EVIDENCE_1"],
            "valid_citations": ["EVIDENCE_1"],
            "invalid_citations": [],
            "malformed_markers": [],
        },
        "citation_retry_used": False,
    }


async def fake_generator_with_evidence(
    complaint,
    top_k=5,
):
    return fake_generation_result_with_evidence()


def create_generated_complaint(
    client,
    token: str,
    monkeypatch,
):
    monkeypatch.setattr(
        ("app.services." "complaint_generation_service." "generate_grounded_complaint"),
        fake_generator_with_evidence,
    )

    draft = create_draft_complaint(
        client,
        token,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{draft['id']}/generate"),
        headers=auth_headers(token),
        json={"regenerate": False},
    )

    assert response.status_code == 200, response.text

    generated = response.json()

    assert generated["status"] == "generated"

    return generated

async def fake_acquire_multiple_evidence_locks(
    evidence_ids,
    user_id,
    operation,
):
    """
    Citation-validation tests use synthetic evidence
    snapshots and do not exercise Mongo lifecycle locking.

    Lifecycle locking has its own dedicated integration
    tests.
    """
    return (
        "test-lifecycle-lock-token",
        [],
    )


async def fake_release_multiple_evidence_locks(
    evidence_ids,
    user_id,
    lock_token,
):
    return None
# =========================================================
# 1. PERSISTENCE
# =========================================================


def test_generation_persists_evidence_references(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    references = complaint["evidence_references"]

    assert len(references) == 1

    reference = references[0]

    assert reference["citation_id"] == "EVIDENCE_1"

    assert reference["original_filename"] == "invoice.txt"

    assert reference["sha256"] == "a" * 64

    assert "extracted_text" not in reference

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    saved = response.json()

    assert saved["evidence_references"][0]["citation_id"] == "EVIDENCE_1"


# =========================================================
# 2. VALID EVIDENCE EDIT
# =========================================================


def test_valid_evidence_citation_in_edit_is_allowed(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    edited_text = (
        "To,\n"
        "[Appropriate Authority]\n\n"
        "Subject: Edited complaint\n\n"
        "The uploaded invoice records a purchase "
        "amount of INR 25,000. [EVIDENCE_1]\n\n"
        "The relevant legal basis is supported by "
        "the authoritative source. [SOURCE_1]\n\n"
        "I request appropriate relief."
    )

    response = client.patch(
        (f"/api/v1/complaints/" f"{complaint['id']}/generated-text"),
        headers=auth_headers(token),
        json={"generated_text": edited_text},
    )

    assert response.status_code == 200, response.text

    updated = response.json()

    assert updated["status"] == "edited"

    assert "[EVIDENCE_1]" in updated["generated_text"]


# =========================================================
# 3. UNKNOWN EVIDENCE EDIT
# =========================================================


def test_unknown_evidence_citation_in_edit_is_rejected(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    response = client.patch(
        (f"/api/v1/complaints/" f"{complaint['id']}/generated-text"),
        headers=auth_headers(token),
        json={
            "generated_text": (
                "The uploaded document allegedly "
                "contains relevant information. "
                "[EVIDENCE_999]\n\n"
                "The legal basis is supported by "
                "the authoritative source. "
                "[SOURCE_1]"
            )
        },
    )

    assert response.status_code == 400, response.text

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    saved = response.json()

    assert "[EVIDENCE_999]" not in saved["generated_text"]

    assert saved["status"] == "generated"


# =========================================================
# 4. VALID FINALIZATION
# =========================================================


def test_valid_source_and_evidence_can_be_finalized(
    client,
    monkeypatch,
):
    async def fake_consistency(
        complaint,
        user_id,
        citation_ids=None,
    ):

        return {
            "consistent": True,
            "has_evidence_references": True,
            "checked_count": 1,
            "results": [],
            "issues": [],
        }

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_service."
            "validate_complaint_evidence_consistency"
        ),
        fake_consistency,
    )

    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    monkeypatch.setattr(
        "app.services.complaint_service."
        "acquire_multiple_evidence_locks",
        fake_acquire_multiple_evidence_locks,
    )

    monkeypatch.setattr(
        "app.services.complaint_service."
        "release_multiple_evidence_locks",
        fake_release_multiple_evidence_locks,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )

    assert response.status_code == 200, response.text

    finalized = response.json()

    assert finalized["status"] == "finalized"

    assert finalized["finalized_at"] is not None

    assert finalized["evidence_references"]


# =========================================================
# 5. INVALID FINALIZATION
# =========================================================


def test_finalization_rejects_unknown_evidence_citation(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    corrupted_text = (
        "The uploaded document contains a payment "
        "record. [EVIDENCE_999]\n\n"
        "The relevant legal basis is supported by "
        "the authoritative source. [SOURCE_1]"
    )

    async def corrupt_saved_text():
        return await update_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
            update_data={
                "generated_text": corrupted_text,
            },
        )

    corrupted = client.portal.call(corrupt_saved_text)

    assert corrupted is not None

    response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )

    assert response.status_code == 409, response.text

    saved_response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert saved_response.status_code == 200

    saved = saved_response.json()

    assert saved["status"] == "generated"

    assert saved["finalized_at"] is None


# =========================================================
# 6. EVIDENCE CITATION OPTIONAL
# =========================================================


def test_finalization_does_not_require_evidence_citation(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    edited_text = (
        "To,\n"
        "[Appropriate Authority]\n\n"
        "Subject: Consumer complaint\n\n"
        "I submit this complaint based on the facts "
        "I have provided.\n\n"
        "The relevant legal basis is supported by "
        "the authoritative legal source. "
        "[SOURCE_1]\n\n"
        "I request appropriate relief."
    )

    edit_response = client.patch(
        (f"/api/v1/complaints/" f"{complaint['id']}/generated-text"),
        headers=auth_headers(token),
        json={"generated_text": edited_text},
    )

    assert edit_response.status_code == 200, edit_response.text

    assert "[EVIDENCE_" not in edit_response.json()["generated_text"]

    finalize_response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )

    assert finalize_response.status_code == 200, finalize_response.text

    assert finalize_response.json()["status"] == "finalized"
    finalized = finalize_response.json()

    assert finalized["status"] == "finalized"

    assert finalized["evidence_references"] == []


# =========================================================
# 7. PRIVACY
# =========================================================


def test_complaint_response_does_not_expose_extracted_text(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    unsafe_references = [
        {
            "citation_id": "EVIDENCE_1",
            "evidence_id": str(ObjectId()),
            "complaint_id": complaint["id"],
            "title": "Private invoice",
            "original_filename": "private.txt",
            "evidence_type": "text",
            "media_type": "text/plain",
            "sha256": "b" * 64,
            "extraction_method": "utf8_text",
            "extracted_page_count": None,
            "included_characters": 100,
            "truncated": False,
            "extracted_text": "HIGHLY PRIVATE RAW EVIDENCE TEXT",
        }
    ]

    async def inject_unsafe_metadata():
        return await update_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
            update_data={
                "evidence_references": unsafe_references,
            },
        )

    updated = client.portal.call(inject_unsafe_metadata)

    assert updated is not None

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "HIGHLY PRIVATE RAW EVIDENCE TEXT" not in response.text

    assert "extracted_text" not in data["evidence_references"][0]
