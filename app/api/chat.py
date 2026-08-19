from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)

from app.core.dependencies import get_current_user
from app.schemas.chat import (
    ChatCreate,
    ChatDetailResponse,
    ChatResponse,
    ChatTurnResponse,
    ChatUpdate,
    MessageCreate,
    MessageResponse,
)
from app.services.chat_service import (
    create_legal_chat_turn,
    create_session,
    delete_session,
    find_session,
    list_session_messages,
    list_user_sessions,
    update_session,
    retry_failed_assistant_message,
)

router = APIRouter(
    prefix="/api/v1/chats",
    tags=["Chats"],
)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    chat_data: ChatCreate,
    current_user: dict = Depends(get_current_user),
):
    chat = await create_session(
        user_id=current_user["_id"],
        title=chat_data.title,
        category=chat_data.category.value,
    )

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat session could not be created",
        )

    return {
        "id": str(chat["_id"]),
        "title": chat["title"],
        "category": chat["category"],
        "created_at": chat["created_at"],
        "updated_at": chat["updated_at"],
    }


@router.get(
    "",
    response_model=list[ChatResponse],
    status_code=status.HTTP_200_OK,
)
async def get_chats(
    current_user: dict = Depends(get_current_user),
):
    chats = await list_user_sessions(
        user_id=current_user["_id"],
    )

    return [
        {
            "id": str(chat["_id"]),
            "title": chat["title"],
            "category": chat["category"],
            "created_at": chat["created_at"],
            "updated_at": chat["updated_at"],
        }
        for chat in chats
    ]


@router.get(
    "/{session_id}",
    response_model=ChatDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    messages = await list_session_messages(
        session_id=session["_id"],
    )

    return {
        "id": str(session["_id"]),
        "title": session["title"],
        "category": session["category"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "messages": [
            {
                "id": str(message["_id"]),
                "session_id": str(message["session_id"]),
                "role": message["role"],
                "content": message["content"],
                "sources": message.get("sources", []),
                "status": message.get("status", "completed"),
                "created_at": message["created_at"],
            }
            for message in messages
        ],
    }


@router.patch(
    "/{session_id}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def update_chat(
    session_id: str,
    chat_data: ChatUpdate,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    update_data = chat_data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    if "category" in update_data:
        update_data["category"] = update_data["category"].value

    updated_session = await update_session(
        session_id=session["_id"],
        user_id=current_user["_id"],
        update_data=update_data,
    )

    if not updated_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    return {
        "id": str(updated_session["_id"]),
        "title": updated_session["title"],
        "category": updated_session["category"],
        "created_at": updated_session["created_at"],
        "updated_at": updated_session["updated_at"],
    }


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_chat(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    deleted = await delete_session(
        session_id=session["_id"],
        user_id=current_user["_id"],
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{session_id}/messages",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    session_id: str,
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    result = await create_legal_chat_turn(
        session_id=session["_id"],
        user_id=current_user["_id"],
        content=message_data.content,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    user_message = result["user_message"]
    assistant_message = result["assistant_message"]

    return {
        "user_message": {
            "id": str(user_message["_id"]),
            "session_id": str(user_message["session_id"]),
            "role": user_message["role"],
            "content": user_message["content"],
            "sources": user_message.get("sources", []),
            "status": user_message.get("status", "completed"),
            "created_at": user_message["created_at"],
        },
        "assistant_message": {
            "id": str(assistant_message["_id"]),
            "session_id": str(assistant_message["session_id"]),
            "role": assistant_message["role"],
            "content": assistant_message["content"],
            "sources": assistant_message.get("sources", []),
            "status": assistant_message.get("status", "completed"),
            "created_at": assistant_message["created_at"],
        },
    }


# ✅ NEW RETRY ENDPOINT
@router.post(
    "/{session_id}/messages/{message_id}/retry",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def retry_message(
    session_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    try:
        message = await retry_failed_assistant_message(
            session_id=session["_id"],
            message_id=message_id,
            user_id=current_user["_id"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return {
        "id": str(message["_id"]),
        "session_id": str(message["session_id"]),
        "role": message["role"],
        "content": message["content"],
        "sources": message.get("sources", []),
        "status": message.get("status", "completed"),
        "created_at": message["created_at"],
    }


@router.get(
    "/{session_id}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_200_OK,
)
async def list_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    session = await find_session(
        session_id=session_id,
        user_id=current_user["_id"],
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )

    messages = await list_session_messages(
        session_id=session["_id"],
    )

    return [
    {
        "id": str(message["_id"]),
        "session_id": str(message["session_id"]),
        "role": message["role"],
        "content": message["content"],
        "sources": message.get("sources", []),
        "status": message.get("status", "completed"),
        "created_at": message["created_at"],
    }
    for message in messages
]