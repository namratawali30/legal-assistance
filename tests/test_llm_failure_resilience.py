from types import SimpleNamespace

import pytest

from bson import ObjectId

from app.rag import llm_client

from app.rag.llm_client import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
)

import app.services.chat_service as chat_service

import app.services.complaint_generation_service as complaint_generation_service



# =========================================================
# TEST PROVIDER CLIENT
# =========================================================


class FakeCompletionEndpoint:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error

    async def create(
        self,
        **kwargs,
    ):
        if self.error is not None:
            raise self.error

        return self.result


def fake_openrouter_client(
    *,
    result=None,
    error=None,
):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=FakeCompletionEndpoint(
                result=result,
                error=error,
            )
        )
    )


def fake_openrouter_response(
    content,
):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                )
            )
        ]
    )


# =========================================================
# CLIENT FAILURE NORMALIZATION
# =========================================================


def test_missing_llm_configuration_is_service_error(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        llm_client,
        "_client",
        None,
    )

    monkeypatch.setattr(
        llm_client.settings,
        "llm_api_key",
        None,
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMServiceError
    ):
        client.portal.call(
            exercise
        )


def test_client_creation_failure_is_normalized(
    client,
    monkeypatch,
):
    def fail_client_creation():
        raise RuntimeError(
            "provider SDK initialization secret"
        )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        fail_client_creation,
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMServiceError,
        match="LLM generation failed",
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "provider SDK initialization secret"
        not in str(exc_info.value)
    )


def test_rate_limit_is_normalized(
    client,
    monkeypatch,
):
    class FakeRateLimitError(Exception):
        pass

    monkeypatch.setattr(
        llm_client,
        "RateLimitError",
        FakeRateLimitError,
    )

    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            error=FakeRateLimitError(
                "raw provider quota details"
            )
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMRateLimitError,
        match="rate limit exceeded",
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "raw provider quota details"
        not in str(exc_info.value)
    )


def test_timeout_is_normalized(
    client,
    monkeypatch,
):
    class FakeTimeoutError(Exception):
        pass

    monkeypatch.setattr(
        llm_client,
        "APITimeoutError",
        FakeTimeoutError,
    )

    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            error=FakeTimeoutError(
                "raw timeout internals"
            )
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMTimeoutError,
        match="request timed out",
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "raw timeout internals"
        not in str(exc_info.value)
    )


def test_connection_failure_is_normalized(
    client,
    monkeypatch,
):
    class FakeConnectionError(Exception):
        pass

    monkeypatch.setattr(
        llm_client,
        "APIConnectionError",
        FakeConnectionError,
    )

    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            error=FakeConnectionError(
                "provider hostname details"
            )
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMConnectionError,
        match=(
            "Could not connect "
            "to LLM provider"
        ),
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "provider hostname details"
        not in str(exc_info.value)
    )


def test_unexpected_provider_failure_is_normalized(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            error=RuntimeError(
                "sensitive upstream response"
            )
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMServiceError,
        match="LLM generation failed",
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "sensitive upstream response"
        not in str(exc_info.value)
    )


# =========================================================
# RESPONSE VALIDATION
# =========================================================


@pytest.mark.parametrize(
    "content",
    [
        None,
        "",
        "   ",
        "\n\t",
    ],
)
def test_empty_provider_response_fails_closed(
    client,
    monkeypatch,
    content,
):
    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    response = fake_openrouter_response(
        content
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            result=response
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    with pytest.raises(
        LLMServiceError,
        match="empty response",
    ):
        client.portal.call(
            exercise
        )


def test_valid_response_is_trimmed(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        llm_client.settings,
        "llm_provider",
        "openrouter",
    )

    response = fake_openrouter_response(
        "  grounded answer  "
    )

    monkeypatch.setattr(
        llm_client,
        "get_llm_client",
        lambda: fake_openrouter_client(
            result=response
        ),
    )

    async def exercise():
        return await llm_client.generate_text(
            instructions="system",
            input_text="question",
        )

    result = client.portal.call(
        exercise
    )

    assert result == "grounded answer"


# =========================================================
# CHAT FAIL-CLOSED BEHAVIOR
# =========================================================


def test_chat_provider_failure_creates_failed_message(
    client,
    monkeypatch,
):
    session_id = ObjectId()
    user_id = ObjectId()

    session = {
        "_id": session_id,
        "user_id": user_id,
        "category": "consumer_rights",
    }

    created_messages = []

    async def fake_get_session(
        session_id,
        user_id,
    ):
        return session

    async def fake_get_messages(
        session_id,
        user_id=None,
    ):
        return []

    async def fake_create_message(
        document,
    ):
        created_messages.append(
            dict(document)
        )

        return ObjectId()

    async def fake_update_session(
        **kwargs,
    ):
        return session

    async def fail_generation(
        **kwargs,
    ):
        raise LLMTimeoutError(
            "raw provider detail"
        )

    monkeypatch.setattr(
        chat_service,
        "get_chat_session",
        fake_get_session,
    )

    monkeypatch.setattr(
        chat_service,
        "get_session_messages",
        fake_get_messages,
    )

    monkeypatch.setattr(
        chat_service,
        "create_message",
        fake_create_message,
    )

    monkeypatch.setattr(
        chat_service,
        "update_chat_session",
        fake_update_session,
    )

    monkeypatch.setattr(
        chat_service,
        "generate_legal_answer",
        fail_generation,
    )

    async def exercise():
        return await (
            chat_service
            .create_legal_chat_turn(
                session_id=session_id,
                user_id=user_id,
                content=(
                    "What consumer remedy "
                    "may apply?"
                ),
            )
        )

    result = client.portal.call(
        exercise
    )

    assistant = result[
        "assistant_message"
    ]

    assert (
        assistant["status"]
        == "failed"
    )

    assert (
        assistant["sources"]
        == []
    )

    assert (
        assistant["content"]
        == chat_service
        .LLM_TEMPORARY_FAILURE_MESSAGE
    )

    assert (
        "raw provider detail"
        not in assistant["content"]
    )

    # User message and failed assistant message
    # must both be persisted.
    assert len(
        created_messages
    ) == 2

    assert (
        created_messages[0]["role"]
        == "user"
    )

    assert (
        created_messages[1]["role"]
        == "assistant"
    )

    assert (
        created_messages[1]["status"]
        == "failed"
    )


# =========================================================
# COMPLAINT FAIL-CLOSED BEHAVIOR
# =========================================================


def test_complaint_provider_failure_does_not_update_complaint(
    client,
    monkeypatch,
):
    complaint_id = ObjectId()
    user_id = ObjectId()

    complaint = {
        "_id": complaint_id,
        "user_id": user_id,
        "status": "draft",
        "revision": 0,
        "generated_text": None,
    }

    update_called = False

    async def fake_get_complaint(
        complaint_id,
        user_id,
    ):
        return complaint

    async def fail_generation(
        **kwargs,
    ):
        raise LLMServiceError(
            "raw upstream provider response"
        )

    async def fake_update(
        **kwargs,
    ):
        nonlocal update_called

        update_called = True

        return None

    monkeypatch.setattr(
        complaint_generation_service,
        "get_complaint",
        fake_get_complaint,
    )

    monkeypatch.setattr(
        complaint_generation_service,
        "generate_grounded_complaint",
        fail_generation,
    )

    monkeypatch.setattr(
        complaint_generation_service,
        "update_complaint_if_unchanged",
        fake_update,
    )

    async def exercise():
        return await (
            complaint_generation_service
            .generate_complaint_for_user(
                complaint_id=complaint_id,
                user_id=user_id,
            )
        )

    with pytest.raises(
        complaint_generation_service
        .ComplaintLLMUnavailableError,
        match=(
            "temporarily unavailable"
        ),
    ) as exc_info:
        client.portal.call(
            exercise
        )

    assert (
        "raw upstream provider response"
        not in str(exc_info.value)
    )

    assert update_called is False