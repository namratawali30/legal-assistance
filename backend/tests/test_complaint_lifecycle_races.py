import uuid
from pathlib import Path

from bson import ObjectId

from app.repositories.complaint_repository import (
    acquire_complaint_lifecycle_lock,
    delete_complaint,
    release_complaint_lifecycle_lock,
)
from app.services import (
    evidence_service,
    evidence_storage_service,
)
from app.services.complaint_lifecycle_lock_service import (
    acquire_complaint_lock,
    release_complaint_lock,
)

# =========================================================
# HELPERS
# =========================================================


def unique_email() -> str:
    return f"complaint-lifecycle-" f"{uuid.uuid4().hex[:10]}" "@example.com"


def auth_headers(
    token: str,
) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_account_and_token(
    client,
) -> str:
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Complaint Lifecycle Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code in {
        200,
        201,
    }, response.text

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200, response.text

    token = response.json().get("access_token") or response.json().get("token")

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
            "title": "Complaint lifecycle race",
            "category": "consumer_rights",
            "complainant_name": "Lifecycle Test User",
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
    complaint_id: str,
    content: bytes = (b"Invoice LIFECYCLE-001\n" b"Amount paid: INR 25,000"),
):
    return client.post(
        "/api/v1/evidence",
        headers=auth_headers(token),
        data={
            "complaint_id": complaint_id,
            "title": "Purchase invoice",
        },
        files={
            "file": (
                "invoice.txt",
                content,
                "text/plain",
            )
        },
    )


def acquire_manual_lock(
    client,
    complaint: dict,
    operation: str,
    lease_seconds: int = 300,
):
    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    lock_token = uuid.uuid4().hex

    async def acquire():
        return await acquire_complaint_lifecycle_lock(
            complaint_id=complaint_id,
            user_id=user_id,
            lock_token=lock_token,
            operation=operation,
            lease_seconds=lease_seconds,
        )

    locked = client.portal.call(acquire)

    return (
        complaint_id,
        user_id,
        lock_token,
        locked,
    )


def release_manual_lock(
    client,
    complaint_id,
    user_id,
    lock_token: str,
):
    async def release():
        return await release_complaint_lifecycle_lock(
            complaint_id=complaint_id,
            user_id=user_id,
            lock_token=lock_token,
        )

    return client.portal.call(release)


def stored_files(
    upload_root,
) -> list[Path]:
    root = Path(upload_root)

    if not root.exists():
        return []

    return [path for path in root.rglob("*") if path.is_file()]


# =========================================================
# ACTIVE UPLOAD LEASE VS DELETE
# =========================================================


def test_active_complaint_lock_blocks_delete(
    client,
):
    token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        token,
    )

    (
        complaint_id,
        user_id,
        lock_token,
        locked,
    ) = acquire_manual_lock(
        client,
        complaint,
        operation="simulated_upload",
    )

    assert locked

    try:
        response = client.delete(
            (f"/api/v1/complaints/" f"{complaint['id']}"),
            headers=auth_headers(token),
        )

        assert response.status_code == 409, response.text

        # Complaint must still exist.
        response = client.get(
            (f"/api/v1/complaints/" f"{complaint['id']}"),
            headers=auth_headers(token),
        )

        assert response.status_code == 200

    finally:
        release_manual_lock(
            client,
            complaint_id,
            user_id,
            lock_token,
        )


# =========================================================
# DELETE SUCCEEDS AFTER LEASE RELEASE
# =========================================================


def test_delete_succeeds_after_complaint_lock_release(
    client,
):
    token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        token,
    )

    (
        complaint_id,
        user_id,
        lock_token,
        locked,
    ) = acquire_manual_lock(
        client,
        complaint,
        operation="temporary_blocker",
    )

    assert locked

    released = release_manual_lock(
        client,
        complaint_id,
        user_id,
        lock_token,
    )

    assert released

    response = client.delete(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 204, response.text

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404


# =========================================================
# ACTIVE DELETE LEASE VS UPLOAD
# =========================================================


def test_active_complaint_lock_blocks_evidence_upload_and_cleans_file(
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

    complaint = create_complaint(
        client,
        token,
    )

    (
        complaint_id,
        user_id,
        lock_token,
        locked,
    ) = acquire_manual_lock(
        client,
        complaint,
        operation="simulated_delete",
    )

    assert locked

    try:
        response = upload_evidence(
            client,
            token,
            complaint["id"],
        )

        assert response.status_code == 409, response.text

        # The physical file was written before the
        # complaint lease attempt, so the conflict path
        # must clean it up.
        assert stored_files(upload_root) == []

        # No evidence metadata should have been created.
        response = client.get(
            "/api/v1/evidence",
            headers=auth_headers(token),
            params={
                "complaint_id": complaint["id"],
            },
        )

        assert response.status_code == 200, response.text

        assert response.json() == []

    finally:
        release_manual_lock(
            client,
            complaint_id,
            user_id,
            lock_token,
        )


# =========================================================
# UPLOAD SUCCEEDS AFTER DELETE LEASE RELEASE
# =========================================================


def test_evidence_upload_succeeds_after_complaint_lock_release(
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

    complaint = create_complaint(
        client,
        token,
    )

    (
        complaint_id,
        user_id,
        lock_token,
        locked,
    ) = acquire_manual_lock(
        client,
        complaint,
        operation="temporary_delete",
    )

    assert locked

    released = release_manual_lock(
        client,
        complaint_id,
        user_id,
        lock_token,
    )

    assert released

    response = upload_evidence(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 201, response.text

    evidence = response.json()

    assert evidence["complaint_id"] == complaint["id"]

    assert len(stored_files(upload_root)) == 1


# =========================================================
# LINKED EVIDENCE WINS BEFORE DELETE
# =========================================================


def test_delete_detects_evidence_after_upload_releases_lease(
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

    response = upload_evidence(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 201, response.text

    evidence = response.json()

    # Successful upload has already released its short
    # complaint lifecycle lease. Deletion can now acquire
    # the lease, but must observe the linked evidence.
    response = client.delete(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 409, response.text

    assert "evidence" in (response.text.lower())

    # After removing the child evidence, complaint
    # deletion becomes valid.
    response = client.delete(
        (f"/api/v1/evidence/" f"{evidence['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 204, response.text

    response = client.delete(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 204, response.text


# =========================================================
# COMPLAINT DISAPPEARS DURING UPLOAD
# =========================================================


def test_complaint_deleted_before_upload_binding_returns_404_and_cleans_file(
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

    complaint = create_complaint(
        client,
        token,
    )

    real_acquire = evidence_service.acquire_complaint_lock

    deleted_once = False

    async def delete_then_acquire(
        complaint_id,
        user_id,
        operation,
        lease_seconds=300,
    ):
        nonlocal deleted_once

        if not deleted_once:
            deleted_once = True

            deleted = await delete_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
            )

            assert deleted

        return await real_acquire(
            complaint_id=complaint_id,
            user_id=user_id,
            operation=operation,
            lease_seconds=lease_seconds,
        )

    monkeypatch.setattr(
        evidence_service,
        "acquire_complaint_lock",
        delete_then_acquire,
    )

    response = upload_evidence(
        client,
        token,
        complaint["id"],
    )

    assert response.status_code == 404, response.text

    # File must be removed because no evidence metadata
    # was allowed to bind to the deleted complaint.
    assert stored_files(upload_root) == []

    response = client.get(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
    )

    assert response.status_code == 404


# =========================================================
# EXPIRED LEASE RECOVERY
# =========================================================


def test_expired_complaint_lifecycle_lock_can_be_recovered(
    client,
):
    token = create_account_and_token(client)

    complaint = create_complaint(
        client,
        token,
    )

    (
        complaint_id,
        user_id,
        stale_token,
        stale_lock,
    ) = acquire_manual_lock(
        client,
        complaint,
        operation="expired_test_lock",
        lease_seconds=0,
    )

    assert stale_lock

    async def acquire_replacement():
        return await acquire_complaint_lock(
            complaint_id=complaint_id,
            user_id=user_id,
            operation="replacement_operation",
        )

    (
        replacement_token,
        replacement_complaint,
    ) = client.portal.call(acquire_replacement)

    assert replacement_token

    assert replacement_token != stale_token

    assert replacement_complaint["lifecycle_lock_token"] == replacement_token

    try:
        assert (
            replacement_complaint["lifecycle_lock_operation"] == "replacement_operation"
        )

    finally:

        async def release():
            return await release_complaint_lock(
                complaint_id=complaint_id,
                user_id=user_id,
                lock_token=replacement_token,
            )

        client.portal.call(release)
