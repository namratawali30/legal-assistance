from typing import Any

from app.db.documents import (
    build_chat_session_document,
    build_message_document,
)
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

    deleted = await delete_chat_session(
        session_id=session["_id"],
        user_id=user_id,
    )

    return deleted


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