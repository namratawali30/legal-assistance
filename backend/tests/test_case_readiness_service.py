import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app.schemas.readiness import CaseReadinessState
from app.services.case_readiness_service import (
    compute_complaint_readiness,
    compute_session_readiness,
)


@pytest.mark.anyio
async def test_complete_consumer_case_readiness(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {
            "issue": "defective_phone",
            "purchase_date": "2026-01-15",
            "location": "Delhi",
            "seller_refusal": "refused refund",
        },
    }

    mock_evidence = [
        {
            "_id": ObjectId(),
            "user_id": user_id,
            "title": "Invoice.pdf",
            "status": "ready",
        },
        {
            "_id": ObjectId(),
            "user_id": user_id,
            "title": "Chat_Screenshot.png",
            "status": "ready",
        },
    ]

    class FakeCursor:
        async def to_list(self, length):
            return mock_evidence

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    res = await compute_session_readiness(session, user_id)
    assert res.readiness_state == CaseReadinessState.READY_FOR_NEXT_STEP
    assert len(res.facts_established) >= 3
    assert len(res.evidence_available) == 2
    assert res.possible_authority is not None


@pytest.mark.anyio
async def test_missing_critical_fact_returns_needs_information(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {},  # Empty context, missing dates & facts
    }

    class FakeCursor:
        async def to_list(self, length):
            return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    res = await compute_session_readiness(session, user_id)
    assert res.readiness_state == CaseReadinessState.NEEDS_INFORMATION
    assert len(res.facts_missing) > 0


@pytest.mark.anyio
async def test_facts_present_no_evidence_returns_needs_evidence(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {
            "purchase_date": "2026-01-15",
            "location": "Mumbai",
            "seller_refusal": "refused repair",
        },
    }

    class FakeCursor:
        async def to_list(self, length):
            return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    res = await compute_session_readiness(session, user_id)
    assert res.readiness_state == CaseReadinessState.NEEDS_EVIDENCE
    assert len(res.evidence_available) == 0


@pytest.mark.anyio
async def test_requires_ocr_not_treated_as_ready_proof(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {
            "purchase_date": "2026-01-15",
            "location": "Delhi",
            "seller_refusal": "refused",
        },
    }

    mock_evidence = [
        {
            "_id": ObjectId(),
            "user_id": user_id,
            "title": "scanned_receipt.jpg",
            "status": "requires_ocr",  # OCR not done yet
        }
    ]

    class FakeCursor:
        async def to_list(self, length):
            return mock_evidence

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    res = await compute_session_readiness(session, user_id)
    assert res.evidence_available[0].status == "requires_ocr"
    assert "OCR text extraction pending" in res.evidence_available[0].supports


@pytest.mark.anyio
async def test_complaint_readiness_computation(monkeypatch):
    user_id = ObjectId()
    complaint = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "complainant_name": "John Doe",
        "respondent_name": "ABC Retail",
        "incident_date": "2026-02-01",
        "incident_location": "Bangalore",
        "facts": "I bought a TV from ABC Retail on 1 Feb 2026. The TV screen was cracked upon delivery.",
        "evidence_references": [],
        "sources": [],
    }

    class FakeCursor:
        async def to_list(self, length):
            return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    res = await compute_complaint_readiness(complaint, user_id)
    assert len(res.facts_established) >= 3
    assert "District Consumer Disputes" in res.possible_authority
