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
    get_message_by_id,
    get_session_messages,
    get_user_chat_sessions,
    update_chat_session,
    update_message,
)

LLM_TEMPORARY_FAILURE_MESSAGE = (
    "The legal assistance service is temporarily unavailable. "
    "Your question has been saved. Please try again shortly."
)


async def create_session(
    user_id,
    title: str,
    category: str,
    answer_mode: str = "simple",
):
    session_data = build_chat_session_document(
        user_id=user_id,
        title=title,
        category=category,
        answer_mode=answer_mode,
    )

    session_id = await create_chat_session(session_data)


    # The insert already succeeded. Do not introduce
    # another DB read merely to construct the response.
    return {
        **session_data,
        "_id": session_id,
    }


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
    return await get_user_chat_sessions(user_id)


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

    # Delete the authoritative parent first.
    #
    # If parent deletion fails, its history remains intact.
    deleted = await delete_chat_session(
        session_id=session["_id"],
        user_id=user_id,
    )

    if not deleted:
        return False

    # Once the parent no longer exists, any residual
    # messages are inaccessible orphan cleanup rather
    # than a visible chat whose history disappeared.
    try:
        await delete_session_messages(
            session_id=session["_id"],
            user_id=user_id,
        )

    except Exception:
        # Do not turn an already-successful parent
        # deletion into an ambiguous client failure.
        #
        # Internal cleanup diagnostics belong in 09.14.
        pass

    return True


async def add_message(
    session_id,
    user_id,
    role: str,
    content: str,
    sources: list[dict] | None = None,
):
    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )

    if not session:
        return None

    message_data = build_message_document(
        session_id=session["_id"],
        user_id=user_id,
        role=role,
        content=content,
        sources=sources,
    )

    return await create_message(message_data)


async def list_session_messages(
    session_id,
    user_id=None,
):
    return await get_session_messages(
        session_id=session_id,
        user_id=user_id,
    )


from app.services.conversation_decision_service import (
    evaluate_conversation_decision,
    merge_case_context,
)
from app.schemas.decision import DecisionAction


async def create_legal_chat_turn(
    session_id,
    user_id,
    content: str,
    answer_mode: str | None = None,
) -> dict[str, Any] | None:
    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id,
    )

    if not session:
        return None

    # Determine effective answer mode
    effective_answer_mode = answer_mode or session.get("answer_mode", "simple")
    if answer_mode and answer_mode != session.get("answer_mode"):
        await update_chat_session(
            session_id=session["_id"],
            user_id=user_id,
            update_data={"answer_mode": answer_mode},
        )

    # 1. Retrieve previous conversation & session context
    previous_messages = await get_session_messages(session["_id"], user_id=user_id)
    existing_case_context = session.get("case_context", {})
    clarification_count = session.get("clarification_count", 0)
    current_category = session.get("category", "consumer_rights")

    # 2. Run Conversation Decision Engine
    decision = await evaluate_conversation_decision(
        current_message=content,
        category=current_category,
        messages=previous_messages,
        existing_case_context=existing_case_context,
        clarification_count=clarification_count,
    )

    # 3. Update structured case context & category if suggested
    updated_case_context = merge_case_context(
        existing_case_context, decision.case_context_updates
    )

    category_labels = {
        "consumer_rights": "Consumer Rights",
        "labour_rights": "Labour Rights",
        "womens_safety": "Women's Safety",
        "educational_rights": "Educational Rights",
        "anti_ragging": "Anti-Ragging",
    }

    effective_category = current_category
    category_notice = None

    if (
        decision.suggested_category
        and decision.suggested_category in category_labels
        and decision.suggested_category != current_category
    ):
        effective_category = decision.suggested_category
        new_label = category_labels[effective_category]
        category_notice = f"Based on your clarification, this conversation is now being handled under {new_label}."


    # 4. Store user message (always completed)
    user_message_data = build_message_document(
        session_id=session["_id"],
        user_id=user_id,
        role="user",
        content=content,
        sources=[],
        status="completed",
        message_type="user",
    )
    user_message_id = await create_message(user_message_data)

    # 5. Process action
    assistant_content = ""
    assistant_sources = []
    assistant_status = "completed"
    message_type = "answer"
    suggested_options = None
    rag_result = {}

    if decision.action == DecisionAction.ASK_FOLLOW_UP:
        assistant_content = decision.question or "Could you clarify a few more details regarding your situation?"
        message_type = "clarification"
        suggested_options = decision.suggested_options
        clarification_count += 1

    elif decision.action == DecisionAction.REFUSE_UNSUPPORTED:
        assistant_content = decision.question or (
            "I am sorry, but your request appears to be outside the supported legal information scope of this platform."
        )
        message_type = "refusal"

    else:  # DecisionAction.ANSWER
        retrieval_query = build_conversation_query(
            current_question=content,
            messages=previous_messages,
            case_context=updated_case_context,
        )

        try:
            rag_result = await generate_legal_answer(
                question=content,
                category=effective_category,
                top_k=5,
                retrieval_query=retrieval_query,
                case_context=updated_case_context,
                answer_mode=effective_answer_mode,
            )

            assistant_content = rag_result["answer"]
            assistant_sources = rag_result.get("sources", [])
            assistant_status = "failed" if rag_result.get("status") == "llm_unavailable" else "completed"
            message_type = "answer"
        except (
            LLMRateLimitError,
            LLMTimeoutError,
            LLMConnectionError,
            LLMServiceError,
        ):
            assistant_content = LLM_TEMPORARY_FAILURE_MESSAGE
            assistant_sources = []
            assistant_status = "failed"
            message_type = "answer"
            rag_result = {
                "answer": LLM_TEMPORARY_FAILURE_MESSAGE,
                "sources": [],
                "status": "llm_unavailable",
            }

    # 6. Store assistant response document
    assistant_message_data = build_message_document(
        session_id=session["_id"],
        user_id=user_id,
        role="assistant",
        content=assistant_content,
        sources=assistant_sources,
        status=assistant_status,
        message_type=message_type,
        suggested_options=suggested_options,
        category_notice=category_notice,
    )
    assistant_message_id = await create_message(assistant_message_data)

    # 7. Update chat session in MongoDB
    session_update_data = {
        "case_context": updated_case_context,
        "clarification_count": clarification_count,
        "category": effective_category,
    }
    await update_chat_session(
        session_id=session["_id"],
        user_id=user_id,
        update_data=session_update_data,
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
        raise ValueError("Only assistant messages can be retried")

    # 4. Only failed messages can be retried.
    if (
        failed_message.get(
            "status",
            "completed",
        )
        != "failed"
    ):
        raise ValueError("Only failed assistant messages can be retried")

    # 5. Retrieve conversation history.
    messages = await get_session_messages(
        session_id=session["_id"],
        user_id=user_id,
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
        raise ValueError("Original user message could not be found")

    question = original_user_message["content"]

    # 7. Build conversation-aware retrieval context
    # using messages BEFORE the original question.
    prior_messages = []

    for message in messages:
        if message["_id"] == original_user_message["_id"]:
            break

        prior_messages.append(message)

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
            "sources": rag_result["sources"],
            "status": "completed",
        },
    )

    return updated_message
