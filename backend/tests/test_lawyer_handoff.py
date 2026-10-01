import pytest
from bson import ObjectId
from unittest.mock import AsyncMock, MagicMock, patch


from app.schemas.lawyer_handoff import LawyerHandoffResponse
from app.services.lawyer_handoff_service import (
    build_handoff_docx_export,
    build_handoff_pdf_export,
    generate_session_handoff_pack,
)


@pytest.mark.anyio
async def test_lawyer_handoff_generation_basic():
    user_id = ObjectId()
    session = {
        "_id": ObjectId(),
        "user_id": user_id,
        "category": "consumer_rights",
        "case_context": {
            "issue": "Defective mobile phone",
            "purchase_date": "2026-01-10",
            "seller_refusal": "Seller refused refund",
            "desired_outcome": "Full refund",
        },
    }

    mock_readiness = AsyncMock()
    mock_readiness.facts_established = []
    mock_readiness.facts_missing = []
    mock_readiness.legal_sources = []

    mock_action_plan = AsyncMock()
    mock_action_plan.primary_next_step = "Preserve proof of written complaint."

    with patch("app.services.lawyer_handoff_service.compute_session_readiness", return_value=mock_readiness), \
         patch("app.services.lawyer_handoff_service.generate_session_action_plan", return_value=mock_action_plan), \
         patch("app.services.lawyer_handoff_service.get_user_evidence", new_callable=AsyncMock) as mock_get_ev, \
         patch("app.services.lawyer_handoff_service.get_user_complaints", new_callable=AsyncMock) as mock_get_comp:

        mock_get_ev.return_value = [
            {
                "title": "Invoice PDF",
                "original_filename": "invoice.pdf",
                "evidence_type": "document",
                "media_type": "application/pdf",
                "size_bytes": 1024,
                "sha256": "abc123sha256hashvalue",
                "processing_status": "ready",
            }
        ]
        mock_get_comp.return_value = []


        res = await generate_session_handoff_pack(session, user_id)


        assert isinstance(res, LawyerHandoffResponse)
        assert "Defective mobile phone" in res.case_summary
        assert res.user_objective == "Full refund"
        assert len(res.evidence_index) == 1
        assert res.evidence_index[0].citation_id == "EVIDENCE_1"
        assert res.evidence_index[0].sha256 == "abc123sha256hashvalue"
        assert res.current_next_step == "Preserve proof of written complaint."


def test_pdf_export_generation():
    pack = LawyerHandoffResponse(
        case_summary="Test case summary for legal review.",
        parties=[],
        user_objective="Replacement unit",
        chronology=[],
        established_facts=[],
        unresolved_questions=[],
        evidence_index=[],
        complaint_summary={
            "status": "draft",
            "title": "Draft Complaint",
            "is_finalized": False,
        },
        legal_sources=[],
        actions_already_taken=["Evidence uploaded"],
        current_next_step="Send written notice",
    )

    pdf_bytes = build_handoff_pdf_export(pack)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_docx_export_generation():
    pack = LawyerHandoffResponse(
        case_summary="Test case summary for legal review.",
        parties=[],
        user_objective="Replacement unit",
        chronology=[],
        established_facts=[],
        unresolved_questions=[],
        evidence_index=[],
        complaint_summary={
            "status": "draft",
            "title": "Draft Complaint",
            "is_finalized": False,
        },
        legal_sources=[],
        actions_already_taken=["Evidence uploaded"],
        current_next_step="Send written notice",
    )

    docx_bytes = build_handoff_docx_export(pack)
    assert len(docx_bytes) > 0
    assert b"PK" in docx_bytes[:4]
