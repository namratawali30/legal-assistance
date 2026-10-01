import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app.schemas.action_plan import PlanStatus
from app.services.legal_action_planner_service import (
    generate_complaint_action_plan,
    generate_session_action_plan,
)


@pytest.mark.anyio
async def test_consumer_case_ready_action_plan(monkeypatch):
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
        }
    ]

    class FakeCursor:
        async def to_list(self, length): return mock_evidence

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    plan = await generate_session_action_plan(session, user_id)
    assert plan.status == PlanStatus.PLAN_AVAILABLE
    assert 3 <= len(plan.steps) <= 5
    assert plan.primary_next_step is not None
    assert "District Consumer Disputes" not in plan.primary_next_step or "complaint" in plan.primary_next_step.lower()


@pytest.mark.anyio
async def test_missing_critical_fact_action_plan(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {},  # Empty
    }

    class FakeCursor:
        async def to_list(self, length): return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    plan = await generate_session_action_plan(session, user_id)
    assert plan.status == PlanStatus.NEEDS_MORE_INFORMATION
    assert "Clarify" in plan.primary_next_step


@pytest.mark.anyio
async def test_immediate_safety_prioritization(monkeypatch):
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "anti_ragging",
        "case_context": {
            "institution_type": "college",
            "threats_or_coercion": "physical threats by senior student",
        },
    }

    class FakeCursor:
        async def to_list(self, length): return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    plan = await generate_session_action_plan(session, user_id)
    assert plan.steps[0].priority == "high"
    assert "Safety" in plan.steps[0].title or "Anti-Ragging" in plan.steps[0].title
    assert plan.important_caution is not None


@pytest.mark.anyio
async def test_finalized_complaint_action_plan(monkeypatch):
    user_id = ObjectId()
    complaint = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "complainant_name": "Jane Doe",
        "respondent_name": "Retailer X",
        "incident_date": "2026-01-20",
        "facts": "I ordered goods that were defective and refund was refused.",
        "status": "finalized",
        "sources": [{"citation_id": "SOURCE_1", "title": "Consumer Protection Act, 2019"}],
        "evidence_references": [],
    }

    class FakeCursor:
        async def to_list(self, length): return []

    class FakeDB:
        def __init__(self):
            self.evidence_vault = MagicMock()
            self.evidence_vault.find.return_value = FakeCursor()

    monkeypatch.setattr("app.services.case_readiness_service.database", FakeDB())

    plan = await generate_complaint_action_plan(complaint, user_id)
    assert plan.status == PlanStatus.PLAN_AVAILABLE
    assert "Download Finalized Complaint" in plan.steps[0].title
    assert "locked against further edits" in plan.important_caution.lower()
