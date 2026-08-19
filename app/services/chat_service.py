from typing import Any

from app.rag.llm_client import (
    LLMServiceError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.rag.conversation import (
    build_conversation_query,
)

from app.db.documents import (
    build_chat_session_document,
    build_message_document,
)
from app.rag.answer_generator import generate_legal_answer
from app.repositories.chat_repository import (
    create_chat_session,
    create_message,
    delete_chat_session,
    delete_session_messages,
    get_chat_session,
    get_session_messages,
    get_user_chat_sessions,
    update_chat_session,
)

LLM_TEMPORARY_FAILURE_MESSAGE = (
    "The legal assistance service is temporarily unavailable. "
    "Your question has been saved. Please try again shortly."
)

async def create_session(
    user_id,
    title: str,
    category: str,
):
    session_data = build_chat_session_document(
        user_id=user_id,
        title=title,
        category=category,
    )

    session_id = await create_chat_session(
        session_data
    )

    return await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )


async def find_session(
    session_id,
    user_id,
) -> dict[str, Any] | None:
    return await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )


async def list_user_sessions(
    user_id,
) -> list[dict[str, Any]]:
    return await get_user_chat_sessions(
        user_id
    )


async def update_session(
    session_id,
    user_id,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    return await update_chat_session(
        session_id=session_id,
        user_id=user_id,
        update_data=update_data,
    )


async def delete_session(
    session_id,
    user_id,
) -> bool:
    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )

    if not session:
        return False

    await delete_session_messages(
        session_id=session["_id"],
    )

    return await delete_chat_session(
        session_id=session["_id"],
        user_id=user_id,
    )


async def add_message(
    session_id,
    user_id,
    role: str,
    content: str,
    sources: list[dict] | None = None,
):
    message_data = build_message_document(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=content,
        sources=sources,
    )

    message_id = await create_message(
        message_data
    )

    return message_id


async def list_session_messages(
    session_id,
):
    return await get_session_messages(
        session_id
    )

async def create_legal_chat_turn(
    session_id,
    user_id,
    content: str,
) -> dict[str, Any] | None:
    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )

    if not session:
        return None

    # 1. Retrieve previous conversation
    previous_messages = await get_session_messages(session["_id"])

    # 2. Build retrieval query from history + current question
    retrieval_query = build_conversation_query(
        current_question=content,
        messages=previous_messages,
    )

    # 3. Store user message (always completed)
    user_message_data = build_message_document(
        session_id=session["_id"],
        user_id=user_id,
        role="user",
        content=content,
        sources=[],
        status="completed",
    )
    user_message_id = await create_message(user_message_data)

    try:
        # 4. Run RAG with retrieval query
        rag_result = await generate_legal_answer(
            question=content,
            category=session["category"],
            top_k=5,
            retrieval_query=retrieval_query,
        )
    except (
        LLMRateLimitError,
        LLMTimeoutError,
        LLMConnectionError,
        LLMServiceError,
    ):
        rag_result = {
            "answer": LLM_TEMPORARY_FAILURE_MESSAGE,
            "sources": [],
            "status": "llm_unavailable",  # mark provider failure
        }

    # 5. Determine assistant status
    assistant_status = (
        "failed"
        if rag_result.get("status") == "llm_unavailable"
        else "completed"
    )

    # 6. Store assistant response
    assistant_message_data = build_message_document(
        session_id=session["_id"],
        user_id=user_id,
        role="assistant",
        content=rag_result["answer"],
        sources=rag_result["sources"],
        status=assistant_status,
    )
    assistant_message_id = await create_message(assistant_message_data)

    # 7. Update session timestamp
    await update_chat_session(
        session_id=session["_id"],
        user_id=user_id,
        update_data={},
    )

    return {
        "user_message": {
            **user_message_data,
            "_id": user_message_id,
        },
        "assistant_message": {
            **assistant_message_data,
            "_id": assistant_message_id,
        },
        "rag": rag_result,
    }
async def retry_failed_assistant_message(
    session_id,
    message_id,
    user_id,
) -> dict[str, Any] | None:
    # 1. Verify the chat belongs to the user.
    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )

    if not session:
        return None

    # 2. Find the failed assistant message.
    failed_message = await get_message_by_id(
        message_id=message_id,
        session_id=session["_id"],
        user_id=user_id,
    )

    if not failed_message:
        return None

    # 3. Only assistant messages can be retried.
    if failed_message.get("role") != "assistant":
        raise ValueError(
            "Only assistant messages can be retried"
        )

    # 4. Only failed messages can be retried.
    if failed_message.get(
        "status",
        "completed",
    ) != "failed":
        raise ValueError(
            "Only failed assistant messages can be retried"
        )

    # 5. Retrieve conversation history.
    messages = await get_session_messages(
        session["_id"]
    )

    # Find this assistant message inside the ordered history.
    failed_index = None

    for index, message in enumerate(messages):
        if message["_id"] == failed_message["_id"]:
            failed_index = index
            break

    if failed_index is None:
        return None

    # 6. Find the nearest previous USER message.
    original_user_message = None

    for index in range(
        failed_index - 1,
        -1,
        -1,
    ):
        candidate = messages[index]

        if candidate.get("role") == "user":
            original_user_message = candidate
            break

    if not original_user_message:
        raise ValueError(
            "Original user message could not be found"
        )

    question = original_user_message[
        "content"
    ]

    # 7. Build conversation-aware retrieval context
    # using messages BEFORE the original question.
    prior_messages = []

    for message in messages:
        if (
            message["_id"]
            == original_user_message["_id"]
        ):
            break

        prior_messages.append(
            message
        )

    retrieval_query = build_conversation_query(
        current_question=question,
        messages=prior_messages,
    )

    # 8. Retry the legal RAG pipeline.
    try:
        rag_result = await generate_legal_answer(
            question=question,
            category=session["category"],
            top_k=5,
            retrieval_query=retrieval_query,
        )

    except LLMServiceError:
        # Keep the existing failed message.
        return failed_message

    # 9. Update the SAME assistant message.
    updated_message = await update_message(
        message_id=failed_message["_id"],
        session_id=session["_id"],
        user_id=user_id,
        update_data={
            "content": rag_result["answer"],
            "sources": rag_result[
                "sources"
            ],
            "status": "completed",
        },
    )

    return updated_message
