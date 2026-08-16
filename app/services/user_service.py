from typing import Any

from app.repositories.user_repository import (
    get_user_by_email,
    get_user_by_id,
)


async def find_user_by_email(email: str) -> dict[str, Any] | None:
    return await get_user_by_email(email)


async def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    return await get_user_by_id(user_id)