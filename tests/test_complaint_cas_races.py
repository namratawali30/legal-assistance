import uuid
from datetime import datetime, timezone

from bson import ObjectId

from app.repositories.complaint_repository import (
    get_complaint,
    update_complaint,
    update_complaint_if_unchanged,
)

# =========================================================
# HELPERS
# =========================================================


def unique_email() -> str:
    return f"complaint-cas-{uuid.uuid4().hex[:10]}" "@example.com"


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
            "full_name": "Complaint CAS Test User",
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


def create_draft_complaint(
    client,
    token: str,
):
    response = client.post(
        "/api/v1/complaints",
        headers=auth_headers(token),
        json={
            "title": "CAS race complaint",
            "category": "consumer_rights",
            "complainant_name": "CAS Test User",
            "complainant_address": "Test Address",
            "complainant_contact": "9999999999",
            "respondent_name": "ABC Seller",
            "respondent_address": "Seller Address",
            "incident_date": "2026-08-01",
            "incident_location": "Original City",
            "facts": (
                "I purchased a defective product and "
                "the seller refused to provide a refund."
            ),
            "relief_requested": "Refund of the purchase amount.",
            "additional_details": {},
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def fake_generation_result(
    generated_text: str | None = None,
):
    return {
        "generated": True,
        "generated_text": (
            generated_text
            or (
                "The respondent supplied a defective "
                "product. The relevant authoritative "
                "legal provision supports this "
                "complaint. [SOURCE_1]"
            )
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
                "pdf_url": "https://www.indiacode.nic.in/example.pdf",
            }
        ],
        "evidence_references": [],
    }


async def fake_generator(
    complaint,
    top_k=5,
):
    return fake_generation_result()


def create_generated_complaint(
    client,
    token: str,
    monkeypatch,
):
    monkeypatch.setattr(
        ("app.services." "complaint_generation_service." "generate_grounded_complaint"),
        fake_generator,
    )

    draft = create_draft_complaint(
        client,
        token,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{draft['id']}/generate"),
        headers=auth_headers(token),
        json={
            "regenerate": False,
        },
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "generated"

    return response.json()


def read_stored_complaint(
    client,
    complaint: dict,
):
    complaint_id = ObjectId(complaint["id"])

    user_id = ObjectId(complaint["user_id"])

    async def read():
        return await get_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
        )

    stored = client.portal.call(read)

    assert stored

    return stored


# =========================================================
# REPOSITORY CAS
# =========================================================


def test_only_one_writer_can_use_same_revision(
    client,
):
    token = create_account_and_token(client)

    draft = create_draft_complaint(
        client,
        token,
    )

    complaint_id = ObjectId(draft["id"])

    user_id = ObjectId(draft["user_id"])

    async def run():
        current = await get_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
        )

        assert current

        revision = current.get(
            "revision",
            0,
        )

        status = current.get(
            "status",
            "draft",
        )

        first = await update_complaint_if_unchanged(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=revision,
            expected_status=status,
            update_data={
                "relief_requested": "Writer one won.",
            },
        )

        second = await update_complaint_if_unchanged(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=revision,
            expected_status=status,
            update_data={
                "relief_requested": "Writer two should lose.",
            },
        )

        final = await get_complaint(
            complaint_id=complaint_id,
            user_id=user_id,
        )

        return (
            first,
            second,
            final,
        )

    (
        first,
        second,
        final,
    ) = client.portal.call(run)

    assert first is not None

    assert second is None

    assert final["relief_requested"] == "Writer one won."


# =========================================================
# STRUCTURED EDIT VS FINALIZATION
# =========================================================


def test_structured_edit_cannot_overwrite_concurrent_finalization(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    real_cas = update_complaint_if_unchanged

    injected = False

    async def competing_cas(
        complaint_id,
        user_id,
        expected_revision,
        expected_status,
        update_data,
    ):
        nonlocal injected

        if not injected:
            injected = True

            await update_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                update_data={
                    "status": "finalized",
                    "finalized_at": datetime.now(timezone.utc),
                },
            )

        return await real_cas(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=expected_status,
            update_data=update_data,
        )

    monkeypatch.setattr(
        ("app.services." "complaint_service." "update_complaint_if_unchanged"),
        competing_cas,
    )

    response = client.patch(
        (f"/api/v1/complaints/" f"{complaint['id']}"),
        headers=auth_headers(token),
        json={
            "incident_location": "Stale Writer City",
        },
    )

    assert response.status_code == 409, response.text

    stored = read_stored_complaint(
        client,
        complaint,
    )

    assert stored["status"] == "finalized"

    assert stored["incident_location"] != "Stale Writer City"


# =========================================================
# GENERATED-TEXT EDIT VS FINALIZATION
# =========================================================


def test_generated_text_edit_cannot_overwrite_finalization(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    original_text = complaint["generated_text"]

    real_cas = update_complaint_if_unchanged

    injected = False

    async def competing_cas(
        complaint_id,
        user_id,
        expected_revision,
        expected_status,
        update_data,
    ):
        nonlocal injected

        if not injected:
            injected = True

            await update_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                update_data={
                    "status": "finalized",
                    "finalized_at": datetime.now(timezone.utc),
                },
            )

        return await real_cas(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=expected_status,
            update_data=update_data,
        )

    monkeypatch.setattr(
        ("app.services." "complaint_service." "update_complaint_if_unchanged"),
        competing_cas,
    )

    response = client.patch(
        (f"/api/v1/complaints/" f"{complaint['id']}/generated-text"),
        headers=auth_headers(token),
        json={
            "generated_text": (
                "This stale edit must never replace "
                "the finalized complaint. [SOURCE_1]"
            )
        },
    )

    assert response.status_code == 409, response.text

    stored = read_stored_complaint(
        client,
        complaint,
    )

    assert stored["status"] == "finalized"

    assert stored["generated_text"] == original_text


# =========================================================
# REGENERATION VS FINALIZATION
# =========================================================


def test_regeneration_cannot_overwrite_concurrent_finalization(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    original_text = complaint["generated_text"]

    async def regenerated_result(
        complaint,
        top_k=5,
    ):
        return fake_generation_result(
            generated_text=(
                "This is the regenerated version " "that must lose the race. [SOURCE_1]"
            )
        )

    monkeypatch.setattr(
        ("app.services." "complaint_generation_service." "generate_grounded_complaint"),
        regenerated_result,
    )

    real_cas = update_complaint_if_unchanged

    injected = False

    async def competing_cas(
        complaint_id,
        user_id,
        expected_revision,
        expected_status,
        update_data,
    ):
        nonlocal injected

        if not injected:
            injected = True

            await update_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                update_data={
                    "status": "finalized",
                    "finalized_at": datetime.now(timezone.utc),
                },
            )

        return await real_cas(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=expected_status,
            update_data=update_data,
        )

    monkeypatch.setattr(
        (
            "app.services."
            "complaint_generation_service."
            "update_complaint_if_unchanged"
        ),
        competing_cas,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/generate"),
        headers=auth_headers(token),
        json={
            "regenerate": True,
        },
    )

    assert response.status_code == 409, response.text

    stored = read_stored_complaint(
        client,
        complaint,
    )

    assert stored["status"] == "finalized"

    assert stored["generated_text"] == original_text


# =========================================================
# STALE FINALIZATION SNAPSHOT
# =========================================================


def test_finalization_rejects_stale_complaint_snapshot(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    real_cas = update_complaint_if_unchanged

    injected = False

    async def competing_cas(
        complaint_id,
        user_id,
        expected_revision,
        expected_status,
        update_data,
    ):
        nonlocal injected

        if not injected:
            injected = True

            # Simulate a legitimate edit occurring after
            # finalization validated its old snapshot.
            await update_complaint(
                complaint_id=complaint_id,
                user_id=user_id,
                update_data={
                    "incident_location": "Concurrent Edit City",
                    "status": "edited",
                },
            )

        return await real_cas(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=expected_status,
            update_data=update_data,
        )

    monkeypatch.setattr(
        ("app.services." "complaint_service." "update_complaint_if_unchanged"),
        competing_cas,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/finalize"),
        headers=auth_headers(token),
        json={
            "confirm": True,
        },
    )

    assert response.status_code == 409, response.text

    stored = read_stored_complaint(
        client,
        complaint,
    )

    assert stored["status"] == "edited"

    assert stored["incident_location"] == "Concurrent Edit City"

    assert stored.get("finalized_at") is None


# =========================================================
# TWO FINALIZERS
# =========================================================


def test_two_finalizers_cannot_both_win_same_revision(
    client,
    monkeypatch,
):
    token = create_account_and_token(client)

    complaint = create_generated_complaint(
        client,
        token,
        monkeypatch,
    )

    real_cas = update_complaint_if_unchanged

    injected = False

    async def competing_finalizers(
        complaint_id,
        user_id,
        expected_revision,
        expected_status,
        update_data,
    ):
        nonlocal injected

        if not injected:
            injected = True

            # Simulated competing finalizer wins the
            # exact same revision first.
            winner = await real_cas(
                complaint_id=complaint_id,
                user_id=user_id,
                expected_revision=expected_revision,
                expected_status=expected_status,
                update_data=update_data,
            )

            assert winner is not None

        # Original request now attempts the same stale CAS.
        return await real_cas(
            complaint_id=complaint_id,
            user_id=user_id,
            expected_revision=expected_revision,
            expected_status=expected_status,
            update_data=update_data,
        )

    monkeypatch.setattr(
        ("app.services." "complaint_service." "update_complaint_if_unchanged"),
        competing_finalizers,
    )

    response = client.post(
        (f"/api/v1/complaints/" f"{complaint['id']}/finalize"),
        headers=auth_headers(token),
        json={
            "confirm": True,
        },
    )

    # This request loses the race.
    assert response.status_code == 409, response.text

    # But exactly one competing finalization succeeded.
    stored = read_stored_complaint(
        client,
        complaint,
    )

    assert stored["status"] == "finalized"

    assert stored.get("finalized_at") is not None
