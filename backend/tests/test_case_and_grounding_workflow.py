import pytest
from fastapi.testclient import TestClient

from app.rag.claim_verifier import verify_claim_support


def get_auth_headers(client: TestClient, email: str = "case_test_user@example.com"):
    register_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Case Test User",
    }
    client.post("/api/v1/auth/register", json=register_payload)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_case_creation_and_intake(client: TestClient):
    headers = get_auth_headers(client, "case_intake_user@example.com")
    payload = {
        "title": "Defective Laptop Purchase Complaint",
        "category": "consumer_rights",
        "intake_facts": {
            "complainant_name": "Ramesh Kumar",
            "complainant_address": "123 MG Road, Bengaluru",
            "complainant_phone": "+919876543210",
            "complainant_email": "ramesh@example.com",
            "opposite_party_name": "TechStore Pvt Ltd",
            "opposite_party_address": "45 Brigade Road, Bengaluru",
            "incident_date": "2026-08-15",
            "incident_location": "Bengaluru",
            "transaction_amount": 65000.0,
            "desired_outcome": "Full refund of Rs 65,000 and compensation for delay",
            "narrative_summary": "Laptop stopped working 3 days after purchase. Store refused refund.",
            "missing_information": ["Serial number of unit"],
        },
    }

    create_resp = client.post("/api/v1/cases", json=payload, headers=headers)
    assert create_resp.status_code == 201
    case_data = create_resp.json()
    assert case_data["title"] == "Defective Laptop Purchase Complaint"
    assert case_data["intake_facts"]["complainant_name"] == "Ramesh Kumar"
    assert case_data["status"] == "intake"

    case_id = case_data["id"]
    get_resp = client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == case_id


def test_case_submission_recording(client: TestClient):
    headers = get_auth_headers(client, "case_sub_user@example.com")
    create_resp = client.post(
        "/api/v1/cases",
        json={"title": "E-Commerce Consumer Dispute", "category": "consumer_rights"},
        headers=headers,
    )
    case_id = create_resp.json()["id"]

    sub_payload = {
        "authority_name": "District Consumer Disputes Redressal Commission, Bengaluru Inner",
        "submission_date": "2026-09-30",
        "reference_number": "CC/2026/8942",
        "notes": "Physical copy submitted at commission counter with fee receipt.",
        "acknowledged_by_user": True,
    }
    sub_resp = client.post(f"/api/v1/cases/{case_id}/submission", json=sub_payload, headers=headers)
    assert sub_resp.status_code == 200
    updated_case = sub_resp.json()
    assert updated_case["status"] == "submitted"
    assert updated_case["submission_record"]["reference_number"] == "CC/2026/8942"
    assert updated_case["submission_record"]["acknowledged_by_user"] is True


def test_case_cross_user_access_denial(client: TestClient):
    headers_user_a = get_auth_headers(client, "user_a_case@example.com")
    headers_user_b = get_auth_headers(client, "user_b_case@example.com")

    create_resp = client.post(
        "/api/v1/cases",
        json={"title": "User A Private Matter", "category": "consumer_rights"},
        headers=headers_user_a,
    )
    case_id = create_resp.json()["id"]

    # User B attempts to view User A's case -> 404 / access denied
    get_resp = client.get(f"/api/v1/cases/{case_id}", headers=headers_user_b)
    assert get_resp.status_code == 404

    # User B attempts to patch User A's case -> 404 / access denied
    patch_resp = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"title": "Hacked Title"},
        headers=headers_user_b,
    )
    assert patch_resp.status_code == 404


def test_claim_support_verification():
    sources = [
        {
            "source_id": "consumer_protection_act_2019",
            "citation_key": "SOURCE_1",
            "text": "Section 35: Manner in which complaint shall be made.—(1) A complaint, in relation to any goods sold or delivered or agreed to be sold or delivered or any service provided or agreed to be provided, may be filed with a District Commission.",
        }
    ]

    valid_claims = [
        {
            "claim_text": "A consumer complaint may be filed with a District Commission.",
            "source_id": "SOURCE_1",
            "exact_excerpt": "may be filed with a District Commission.",
        }
    ]
    res_valid = verify_claim_support(valid_claims, sources)
    assert res_valid["passed"] is True
    assert res_valid["verified_claims"] == 1

    invalid_claims = [
        {
            "claim_text": "The seller must be imprisoned for 10 years without trial.",
            "source_id": "SOURCE_1",
            "exact_excerpt": "imprisoned for 10 years without trial.",
        }
    ]
    res_invalid = verify_claim_support(invalid_claims, sources)
    assert res_invalid["passed"] is False
    assert len(res_invalid["unverified_claims"]) == 1


def test_health_liveness_and_readiness_endpoints(client: TestClient):
    liveness_resp = client.get("/health/liveness")
    assert liveness_resp.status_code == 200
    assert liveness_resp.json()["status"] == "ok"

    readiness_resp = client.get("/health/readiness")
    assert readiness_resp.status_code in (200, 503)
    assert "checks" in readiness_resp.json()
