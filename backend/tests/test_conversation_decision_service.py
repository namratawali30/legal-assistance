import pytest
from unittest.mock import AsyncMock, patch
from bson import ObjectId

from app.schemas.decision import ConversationDecision, DecisionAction
from app.services.conversation_decision_service import (
    evaluate_conversation_decision,
    merge_case_context,
    sanitize_prompt_injection,
)
from app.services.chat_service import create_legal_chat_turn


@pytest.mark.anyio
async def test_clear_question_returns_answer():
    decision = await evaluate_conversation_decision(
        current_message="What remedies may be available when a seller refuses to replace a defective product?",
        category="consumer_rights",
        messages=[],
        existing_case_context={},
        clarification_count=0,
    )
    assert decision.action == DecisionAction.ANSWER
    assert decision.reason_code == "CLEAR_DIRECT_QUESTION"


@pytest.mark.anyio
async def test_ambiguous_senior_asks_follow_up():
    mock_llm_response = """{
        "action": "ASK_FOLLOW_UP",
        "question": "Is this a senior student at your college/university, or a senior employee/manager at your workplace?",
        "case_context_updates": { "relationship": "senior" },
        "missing_information": [ "institution_type" ],
        "reason_code": "AMBIGUOUS_RELATIONSHIP",
        "suggested_category": null,
        "suggested_options": ["College / University", "Workplace"]
    }"""
    with patch("app.services.conversation_decision_service.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        decision = await evaluate_conversation_decision(
            current_message="My senior is forcing me to do his work.",
            category="labour_rights",
            messages=[],
            existing_case_context={},
            clarification_count=0,
        )

        assert decision.action == DecisionAction.ASK_FOLLOW_UP
        assert "college" in decision.question.lower() or "workplace" in decision.question.lower()
        assert decision.suggested_options == ["College / University", "Workplace"]


@pytest.mark.anyio
async def test_college_clarification_context_update():
    mock_llm_response = """{
        "action": "ASK_FOLLOW_UP",
        "question": "Has the senior student threatened or intimidated you if you refuse?",
        "case_context_updates": { "relationship": "senior student", "institution_type": "college" },
        "missing_information": [ "threats_or_coercion" ],
        "reason_code": "CHECK_THREATS",
        "suggested_category": "anti_ragging",
        "suggested_options": ["Yes, threatened me", "No threats made"]
    }"""
    with patch("app.services.conversation_decision_service.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        decision = await evaluate_conversation_decision(
            current_message="He is a senior student in my college.",
            category="labour_rights",
            messages=[{"role": "user", "content": "My senior is forcing me to do his work."}],
            existing_case_context={"relationship": "senior"},
            clarification_count=1,
        )

        assert decision.action == DecisionAction.ASK_FOLLOW_UP
        assert decision.suggested_category == "anti_ragging"
        assert decision.case_context_updates.get("institution_type") == "college"


@pytest.mark.anyio
async def test_user_correction_overrides_old_context():
    existing = {"location": "Delhi", "relationship": "manager"}
    updates = {"location": "Noida"}
    merged = merge_case_context(existing, updates)
    assert merged["location"] == "Noida"
    assert merged["relationship"] == "manager"


@pytest.mark.anyio
async def test_unsupported_request_returns_refuse_unsupported():
    mock_llm_response = """{
        "action": "REFUSE_UNSUPPORTED",
        "question": "I cannot provide advice on criminal defense in foreign jurisdictions.",
        "case_context_updates": {},
        "missing_information": [],
        "reason_code": "OUT_OF_SCOPE",
        "suggested_category": null,
        "suggested_options": null
    }"""
    with patch("app.services.conversation_decision_service.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        decision = await evaluate_conversation_decision(
            current_message="How do I evade taxes in Panama?",
            category="consumer_rights",
            messages=[],
            existing_case_context={},
            clarification_count=0,
        )

        assert decision.action == DecisionAction.REFUSE_UNSUPPORTED
        assert "cannot" in decision.question.lower() or "outside" in decision.question.lower()


@pytest.mark.anyio
async def test_clarification_limit_with_sufficient_context_returns_answer():
    mock_llm_response = """{
        "action": "ANSWER",
        "question": null,
        "case_context_updates": {},
        "missing_information": [],
        "reason_code": "SUFFICIENT_CONTEXT"
    }"""
    with patch("app.services.conversation_decision_service.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        decision = await evaluate_conversation_decision(
            current_message="I have already reported to the dean.",
            category="anti_ragging",
            messages=[],
            existing_case_context={"relationship": "senior student"},
            clarification_count=2,
        )
        assert decision.action == DecisionAction.ANSWER


@pytest.mark.anyio
async def test_clarification_limit_with_missing_critical_facts_returns_refuse():
    # LLM attempts to ask follow up when clarification_count >= 2 and missing_information is present
    mock_llm_response = """{
        "action": "ASK_FOLLOW_UP",
        "question": "Did the incident involve physical violence?",
        "case_context_updates": {},
        "missing_information": ["physical_violence_details"],
        "reason_code": "MISSING_CRITICAL_FACTS"
    }"""
    with patch("app.services.conversation_decision_service.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        decision = await evaluate_conversation_decision(
            current_message="I don't want to say.",
            category="womens_safety",
            messages=[],
            existing_case_context={},
            clarification_count=2,
        )
        # Safety guard must override ASK_FOLLOW_UP to REFUSE_UNSUPPORTED (NOT forced ANSWER)
        assert decision.action == DecisionAction.REFUSE_UNSUPPORTED
        assert "cannot provide" in decision.question.lower() or "additional clarification" in decision.question.lower()


@pytest.mark.anyio
async def test_category_change_transparency(monkeypatch):
    session_id = ObjectId()
    user_id = ObjectId()
    session = {
        "_id": session_id,
        "user_id": user_id,
        "category": "labour_rights",
        "case_context": {},
        "clarification_count": 1,
    }

    mock_decision = ConversationDecision(
        action=DecisionAction.ASK_FOLLOW_UP,
        question="Has the senior student threatened or intimidated you?",
        case_context_updates={"relationship": "senior student"},
        suggested_category="anti_ragging",
    )

    async def fake_get_session(*args, **kwargs): return session
    async def fake_get_messages(*args, **kwargs): return []
    async def fake_create_message(doc): return ObjectId()
    async def fake_update_session(*args, **kwargs): return session
    async def fake_eval(*args, **kwargs): return mock_decision

    monkeypatch.setattr("app.services.chat_service.get_chat_session", fake_get_session)
    monkeypatch.setattr("app.services.chat_service.get_session_messages", fake_get_messages)
    monkeypatch.setattr("app.services.chat_service.create_message", fake_create_message)
    monkeypatch.setattr("app.services.chat_service.update_chat_session", fake_update_session)
    monkeypatch.setattr("app.services.chat_service.evaluate_conversation_decision", fake_eval)

    turn = await create_legal_chat_turn(
        session_id=session_id,
        user_id=user_id,
        content="He is a senior student at my college.",
    )

    assistant = turn["assistant_message"]
    assert assistant.get("category_notice") is not None
    assert "Anti-Ragging" in assistant["category_notice"]
