import uuid

from bson import ObjectId

from app.rag.evidence_context import (
    hash_evidence_text,
    sanitize_evidence_text,
)
from app.repositories.complaint_repository import (
    get_complaint,
    update_complaint,
)
from app.repositories.evidence_repository import (
    get_evidence,
    update_evidence,
)
from app.services import (
    evidence_storage_service,
)
from app.services.evidence_consistency_service import (
    validate_complaint_evidence_consistency,
)


def unique_email() -> str:
    return f"evidence-consistency-" f"{uuid.uuid4().hex[:10]}" "@example.com"


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
            "full_name": "Evidence Consistency User",
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


def create_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "Evidence consistency complaint",
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
                "the seller refused to provide a refund "
                "after I reported the defect."
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
    upload_response = client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data={
            "complaint_id": complaint_id,
            "title": "Invoice",
        },
        files={
            "file": (
                "invoice.txt",
                (b"Invoice CONSISTENCY-001\n" b"Amount paid: INR 25,000"),
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201, upload_response.text

    evidence = upload_response.json()

    process_response = client.post(
        (f"/api/v1/evidence/" f"{evidence['id']}/process"),
        headers=auth_headers(token),
        json={"retry": False},
    )

    assert process_response.status_code == 200, process_response.text

    assert process_response.json()["processing_status"] == "ready"

    return evidence


def attach_snapshot(
    client,
    complaint: dict,
    evidence: dict,
):
    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    evidence_id = ObjectId(evidence["id"])

    async def attach():
        current_evidence = await get_evidence(
            evidence_id=evidence_id,
            user_id=user_id,
        )

        assert current_evidence

        normalized = sanitize_evidence_text(current_evidence["extracted_text"])

        text_hash = hash_evidence_text(normalized)

        return await update_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
            update_data={
                "evidence_references": [
                    {
                        "citation_id": "EVIDENCE_1",
                        "evidence_id": str(evidence_id),
                        "complaint_id": str(complaint_id),
                        "title": "Invoice",
                        "original_filename": current_evidence["original_filename"],
                        "evidence_type": current_evidence["evidence_type"],
                        "media_type": current_evidence["media_type"],
                        "sha256": current_evidence["sha256"],
                        "extracted_text_sha256": text_hash,
                        "extraction_method": current_evidence.get("extraction_method"),
                        "extracted_page_count": current_evidence.get(
                            "extracted_page_count"
                        ),
                        "included_characters": len(normalized),
                        "truncated": False,
                    }
                ],
            },
        )

    return client.portal.call(attach)


def run_consistency_check(
    client,
    complaint_id: str,
    user_id: str,
):
    async def check():
        complaint = await get_complaint(
            complaint_id=ObjectId(complaint_id),
            user_id=ObjectId(user_id),
        )

        assert complaint

        return await validate_complaint_evidence_consistency(
            complaint=complaint,
            user_id=ObjectId(user_id),
        )

    return client.portal.call(check)


def test_matching_evidence_snapshot_is_consistent(
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

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    attach_snapshot(
        client,
        complaint,
        evidence,
    )

    result = run_consistency_check(
        client,
        complaint["id"],
        complaint["user_id"],
    )

    assert result["consistent"] is True

    assert result["checked_count"] == 1

    assert result["issues"] == []


def test_changed_extracted_text_is_detected(
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

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    attach_snapshot(
        client,
        complaint,
        evidence,
    )

    async def change_text():
        return await update_evidence(
            evidence_id=ObjectId(evidence["id"]),
            user_id=ObjectId(evidence["user_id"]),
            update_data={
                "extracted_text": (
                    "Invoice CONSISTENCY-001\n" "Amount paid: INR 99,999"
                ),
            },
        )

    client.portal.call(change_text)

    result = run_consistency_check(
        client,
        complaint["id"],
        complaint["user_id"],
    )

    assert result["consistent"] is False

    codes = {issue["code"] for issue in result["issues"]}

    assert "text_snapshot_mismatch" in codes


def test_not_ready_evidence_is_detected(
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

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    attach_snapshot(
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

    result = run_consistency_check(
        client,
        complaint["id"],
        complaint["user_id"],
    )

    assert result["consistent"] is False

    codes = {issue["code"] for issue in result["issues"]}

    assert "evidence_not_ready" in codes


def test_missing_text_snapshot_is_detected(
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

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    updated = attach_snapshot(
        client,
        complaint,
        evidence,
    )

    assert updated

    reference = dict(updated["evidence_references"][0])

    reference.pop(
        "extracted_text_sha256",
        None,
    )

    async def remove_snapshot():
        return await update_complaint(
            complaint_id=ObjectId(complaint["id"]),
            user_id=ObjectId(complaint["user_id"]),
            update_data={
                "evidence_references": [reference],
            },
        )

    client.portal.call(remove_snapshot)

    result = run_consistency_check(
        client,
        complaint["id"],
        complaint["user_id"],
    )

    assert result["consistent"] is False

    codes = {issue["code"] for issue in result["issues"]}

    assert "missing_text_snapshot" in codes


def test_complaint_without_evidence_is_consistent(
    client,
):
    token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        token,
    )

    result = run_consistency_check(
        client,
        complaint["id"],
        complaint["user_id"],
    )

    assert result["consistent"] is True

    assert result["has_evidence_references"] is False

    assert result["checked_count"] == 0
