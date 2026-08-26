import uuid

from bson import ObjectId

from app.rag.evidence_context import (
    hash_evidence_text,
    sanitize_evidence_text,
)
from app.repositories.complaint_repository import (
    update_complaint,
)
from app.repositories.evidence_repository import (
    get_evidence,
    update_evidence,
)
from app.services import (
    evidence_storage_service,
)


def unique_email() -> str:
    return f"finalize-consistency-" f"{uuid.uuid4().hex[:10]}" "@example.com"


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
            "full_name": "Finalization Consistency User",
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


def create_draft(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Evidence consistency finalization",
            "category": "consumer_rights",
            "complainant_name": "Consistency User",
            "complainant_address": "Test Address",
            "complainant_contact": "9999999999",
            "respondent_name": "ABC Seller",
            "respondent_address": "Seller Address",
            "incident_date": "2026-08-01",
            "incident_location": "Test City",
            "facts": (
                "I purchased a defective product and "
                "the seller refused to provide the "
                "requested refund after I reported "
                "the defect."
            ),
            "relief_requested": "Refund of the purchase amount.",
            "additional_details": {},
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def upload_and_process(
    client,
    token: str,
    complaint_id: str,
):
    response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data={
            "complaint_id": complaint_id,
            "title": "Invoice",
        },
        files={
            "file": (
                "invoice.txt",
                (b"Invoice FINAL-001\n" b"Amount paid: INR 25,000"),
                "text/plain",
            )
        },
    )

    assert response.status_code == 201, response.text

    evidence = response.json()

    response = client.post(
        (f"/api/v1/evidence/" f"{evidence['id']}/process"),
        headers=auth_headers(token),
        json={"retry": False},
    )

    assert response.status_code == 200, response.text

    assert response.json()["processing_status"] == "ready"

    return evidence


def seed_generated_complaint(
    client,
    complaint: dict,
    evidence: dict | None = None,
):
    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    async def seed():
        evidence_references = []

        generated_text = (
            "The relevant legal provision supports " "this complaint. [SOURCE_1]"
        )

        if evidence is not None:
            current_evidence = await get_evidence(
                evidence_id=ObjectId(evidence["id"]),
                user_id=user_id,
            )

            assert current_evidence

            normalized = sanitize_evidence_text(current_evidence["extracted_text"])

            evidence_references = [
                {
                    "citation_id": "EVIDENCE_1",
                    "evidence_id": evidence["id"],
                    "complaint_id": complaint["id"],
                    "title": "Invoice",
                    "original_filename": current_evidence["original_filename"],
                    "evidence_type": current_evidence["evidence_type"],
                    "media_type": current_evidence["media_type"],
                    "sha256": current_evidence["sha256"],
                    "extracted_text_sha256": hash_evidence_text(normalized),
                    "extraction_method": current_evidence.get("extraction_method"),
                    "extracted_page_count": current_evidence.get(
                        "extracted_page_count"
                    ),
                    "included_characters": len(normalized),
                    "truncated": False,
                }
            ]

            generated_text = (
                "The uploaded invoice records payment. "
                "[EVIDENCE_1]\n\n"
                "The relevant legal provision supports "
                "this complaint. [SOURCE_1]"
            )

        return await update_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
            update_data={
                "generated_text": generated_text,
                "sources": [
                    {
                        "citation_id": "SOURCE_1",
                        "title": "Consumer Protection Act, 2019",
                        "authority": "India Code",
                        "category": "consumer_rights",
                        "provision_type": "section",
                        "provision_number": "35",
                        "provision_title": "Complaint provision",
                        "page_start": 20,
                        "page_end": 21,
                        "landing_page": "https://www.indiacode.nic.in/",
                        "pdf_url": ("https://www.indiacode.nic.in/" "example.pdf"),
                    }
                ],
                "evidence_references": evidence_references,
                "status": "generated",
            },
        )

    seeded = client.portal.call(seed)

    assert seeded

    return seeded


def finalize(
    client,
    token: str,
    complaint_id: str,
):
    return client.post(
        (f"/api/v1/complaints/" f"{complaint_id}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )


def test_consistent_cited_evidence_allows_finalization(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(client)

    complaint = create_draft(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    seed_generated_complaint(
        client,
        complaint,
        evidence,
    )

    response = finalize(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "finalized"


def test_changed_extracted_text_blocks_finalization(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(client)

    complaint = create_draft(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    seed_generated_complaint(
        client,
        complaint,
        evidence,
    )

    async def change_text():
        return await update_evidence(
            evidence_id=ObjectId(evidence["id"]),
            user_id=ObjectId(evidence["user_id"]),
            update_data={
                "extracted_text": ("Invoice FINAL-001\n" "Amount paid: INR 99,999"),
            },
        )

    client.portal.call(change_text)

    response = finalize(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 409, response.text

    assert "regenerate" in response.text.lower()


def test_not_ready_cited_evidence_blocks_finalization(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(client)

    complaint = create_draft(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    seed_generated_complaint(
        client,
        complaint,
        evidence,
    )

    async def mark_failed():
        return await update_evidence(
            evidence_id=ObjectId(evidence["id"]),
            user_id=ObjectId(evidence["user_id"]),
            update_data={
                "processing_status": "failed",
            },
        )

    client.portal.call(mark_failed)

    response = finalize(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 409, response.text


def test_physical_file_tampering_blocks_finalization(
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

    token = create_account_and_token(client)

    complaint = create_draft(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    seed_generated_complaint(
        client,
        complaint,
        evidence,
    )

    stored_files = [
        path for path in (upload_root / "evidence").rglob("*") if path.is_file()
    ]

    assert len(stored_files) == 1

    stored_files[0].write_bytes(b"Tampered physical evidence.")

    response = finalize(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 409, response.text


def test_no_evidence_references_still_allows_finalization(
    client,
):
    token = create_account_and_token(client)

    complaint = create_draft(
        client,
        token,
    )

    seed_generated_complaint(
        client,
        complaint,
        evidence=None,
    )

    response = finalize(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "finalized"
