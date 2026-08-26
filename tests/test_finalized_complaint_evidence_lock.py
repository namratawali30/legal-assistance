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
    acquire_evidence_lifecycle_lock,
    release_evidence_lifecycle_lock,
    get_evidence,
)
from app.services import (
    evidence_storage_service,
)
from app.services.evidence_lifecycle_service import (
    ensure_evidence_not_finalized_locked,
)


def unique_email() -> str:
    return f"finalized-evidence-lock-" f"{uuid.uuid4().hex[:10]}" "@example.com"


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
            "full_name": "Finalized Evidence Lock User",
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

    token = login_response.json().get("access_token") or login_response.json().get(
        "token"
    )

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
            "title": "Finalized evidence protection",
            "category": "consumer_rights",
            "complainant_name": "Evidence Lock User",
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
                (b"Invoice LOCK-001\n" b"Amount paid: INR 25,000"),
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


def seed_generated_with_evidence(
    client,
    complaint: dict,
    evidence: dict,
):
    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    evidence_id = ObjectId(evidence["id"])

    async def seed():
        current_evidence = await get_evidence(
            evidence_id=evidence_id,
            user_id=user_id,
        )

        assert current_evidence

        normalized = sanitize_evidence_text(current_evidence["extracted_text"])

        return await update_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
            update_data={
                "generated_text": (
                    "The uploaded invoice records "
                    "payment. [EVIDENCE_1]\n\n"
                    "The authoritative legal provision "
                    "supports this complaint. [SOURCE_1]"
                ),
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
                "evidence_references": [
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
                ],
                "status": "generated",
            },
        )

    seeded = client.portal.call(seed)

    assert seeded


def finalize_complaint(
    client,
    token: str,
    complaint_id: str,
):
    response = client.post(
        (f"/api/v1/complaints/" f"{complaint_id}/finalize"),
        headers=auth_headers(token),
        json={"confirm": True},
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "finalized"


def build_finalized_evidence_case(
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

    seed_generated_with_evidence(
        client,
        complaint,
        evidence,
    )

    finalize_complaint(
        client,
        token,
        complaint["id"],
    )

    return (
        token,
        complaint,
        evidence,
    )


def test_finalized_cited_evidence_cannot_be_deleted(
    client,
    monkeypatch,
    tmp_path,
):
    token, complaint, evidence = build_finalized_evidence_case(
        client,
        monkeypatch,
        tmp_path,
    )

    response = client.delete(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 409, response.text

    assert "finalized" in response.text.lower()

    # Evidence still exists.
    response = client.get(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200


def test_finalized_cited_evidence_cannot_be_reprocessed(
    client,
    monkeypatch,
    tmp_path,
):
    token, complaint, evidence = build_finalized_evidence_case(
        client,
        monkeypatch,
        tmp_path,
    )

    response = client.post(
        (f"/api/v1/evidence/" f"{evidence['id']}/process"),
        headers=auth_headers(token),
        json={"retry": True},
    )

    assert response.status_code == 409, response.text

    assert "finalized" in response.text.lower()

    # Processing state remains untouched.
    response = client.get(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 200

    assert response.json()["processing_status"] == "ready"


def test_metadata_edit_remains_allowed_after_finalization(
    client,
    monkeypatch,
    tmp_path,
):
    token, complaint, evidence = build_finalized_evidence_case(
        client,
        monkeypatch,
        tmp_path,
    )

    response = client.patch(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
        json={
            "title": "Archived purchase invoice",
            "description": "Evidence retained for finalized complaint.",
        },
    )

    assert response.status_code == 200, response.text

    updated = response.json()

    assert updated["title"] == "Archived purchase invoice"


def test_non_finalized_cited_evidence_can_still_be_reprocessed(
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

    seed_generated_with_evidence(
        client,
        complaint,
        evidence,
    )

    # Complaint is generated but not finalized.
    response = client.post(
        (f"/api/v1/evidence/" f"{evidence['id']}/process"),
        headers=auth_headers(token),
        json={"retry": True},
    )

    assert response.status_code == 200, response.text

    assert response.json()["processing_status"] == "ready"


def test_non_finalized_evidence_can_be_deleted(
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

    seed_generated_with_evidence(
        client,
        complaint,
        evidence,
    )

    response = client.delete(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 204, response.text

def test_active_lifecycle_lock_blocks_delete(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    user_id = ObjectId(
        complaint["user_id"]
    )

    evidence_id = ObjectId(
        evidence["id"]
    )

    lock_token = uuid.uuid4().hex

    async def acquire():
        return await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=lock_token,
            operation="test_delete_blocker",
        )

    locked = client.portal.call(
        acquire
    )

    assert locked

    try:
        # ---------------------------------------------
        # ACTIVE LOCK MUST BLOCK DELETE
        # ---------------------------------------------

        response = client.delete(
            (
                f"/api/v1/evidence/"
                f"{evidence['id']}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 409, (
            response.text
        )

        # Evidence must still exist after the rejected
        # delete attempt.
        response = client.get(
            (
                f"/api/v1/evidence/"
                f"{evidence['id']}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 200, (
            response.text
        )

    finally:

        async def release():
            await release_evidence_lifecycle_lock(
                evidence_id=evidence_id,
                user_id=user_id,
                lock_token=lock_token,
            )

        client.portal.call(
            release
        )

    # ---------------------------------------------
    # AFTER RELEASE, DELETE MUST WORK
    # ---------------------------------------------

    response = client.delete(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 204, (
        response.text
    )

    # Metadata must also be gone.
    response = client.get(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}"
        ),
        headers=auth_headers(
            token
        ),
    )

    assert response.status_code == 404
def test_active_lifecycle_lock_blocks_reprocessing(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    user_id = ObjectId(
        complaint["user_id"]
    )

    evidence_id = ObjectId(
        evidence["id"]
    )

    lock_token = uuid.uuid4().hex

    async def acquire():
        return await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=lock_token,
            operation="test_reprocess_blocker",
        )

    locked = client.portal.call(
        acquire
    )

    assert locked

    try:
        # Active lifecycle lock must block reprocessing.
        response = client.post(
            (
                f"/api/v1/evidence/"
                f"{evidence['id']}/process"
            ),
            headers=auth_headers(
                token
            ),
            json={
                "retry": True,
            },
        )

        assert response.status_code == 409, (
            response.text
        )

        # Failed contention attempt must not corrupt
        # the evidence processing state.
        response = client.get(
            (
                f"/api/v1/evidence/"
                f"{evidence['id']}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 200, (
            response.text
        )

        assert (
            response.json()[
                "processing_status"
            ]
            == "ready"
        )

    finally:

        async def release():
            await release_evidence_lifecycle_lock(
                evidence_id=evidence_id,
                user_id=user_id,
                lock_token=lock_token,
            )

        client.portal.call(
            release
        )

    # Once the competing lifecycle lease is gone,
    # reprocessing should succeed normally.
    response = client.post(
        (
            f"/api/v1/evidence/"
            f"{evidence['id']}/process"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "retry": True,
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    assert (
        response.json()[
            "processing_status"
        ]
        == "ready"
    )


def test_active_evidence_lock_blocks_finalization(
    client,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        evidence_storage_service.settings,
        "upload_dir",
        str(tmp_path / "uploads"),
    )

    token = create_account_and_token(
        client
    )

    complaint = create_complaint(
        client,
        token,
    )

    evidence = upload_and_process(
        client,
        token,
        complaint["id"],
    )

    seed_generated_with_evidence(
        client,
        complaint,
        evidence,
    )

    user_id = ObjectId(
        complaint["user_id"]
    )

    evidence_id = ObjectId(
        evidence["id"]
    )

    lock_token = uuid.uuid4().hex

    async def acquire():
        return await acquire_evidence_lifecycle_lock(
            evidence_id=evidence_id,
            user_id=user_id,
            lock_token=lock_token,
            operation="simulated_mutation",
        )

    locked = client.portal.call(
        acquire
    )

    assert locked

    try:
        # Active evidence mutation lease must prevent
        # complaint finalization.
        response = client.post(
            (
                f"/api/v1/complaints/"
                f"{complaint['id']}/finalize"
            ),
            headers=auth_headers(
                token
            ),
            json={
                "confirm": True,
            },
        )

        assert response.status_code == 409, (
            response.text
        )

        # Complaint must remain non-finalized.
        response = client.get(
            (
                f"/api/v1/complaints/"
                f"{complaint['id']}"
            ),
            headers=auth_headers(
                token
            ),
        )

        assert response.status_code == 200, (
            response.text
        )

        assert (
            response.json()[
                "status"
            ]
            != "finalized"
        )

    finally:

        async def release():
            await release_evidence_lifecycle_lock(
                evidence_id=evidence_id,
                user_id=user_id,
                lock_token=lock_token,
            )

        client.portal.call(
            release
        )

    # Once the competing evidence lease is released,
    # finalization must succeed because the evidence
    # itself has not changed.
    response = client.post(
        (
            f"/api/v1/complaints/"
            f"{complaint['id']}/finalize"
        ),
        headers=auth_headers(
            token
        ),
        json={
            "confirm": True,
        },
    )

    assert response.status_code == 200, (
        response.text
    )

    assert (
        response.json()[
            "status"
        ]
        == "finalized"
    )