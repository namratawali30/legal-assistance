from typing import Any
from app.db.user_documents import build_user_document
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

async def find_user_by_email(
    email: str,
) -> dict[str, Any] | None:
    return await get_user_by_email(email)


async def find_user_by_id(
    user_id: str,
) -> dict[str, Any] | None:
    return await get_user_by_id(user_id)


async def register_user(
    email: str,
    full_name: str,
    password: str,
) -> dict[str, Any]:
    # 1. Check whether the email is already registered
    existing_user = await get_user_by_email(email)

    if existing_user:
        raise ValueError("Email is already registered")

    # 2. Hash the password
    password_hash = hash_password(password)

    # 3. Build the MongoDB document
    user_document = build_user_document(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
    )

    # 4. Save the user
    user_id = await create_user(user_document)

    # 5. Return safe user information
    return {
        "id": str(user_id),
        "email": user_document["email"],
        "full_name": user_document["full_name"],
        "role": user_document["role"],
        "is_active": user_document["is_active"],
        "created_at": user_document["created_at"],
        "updated_at": user_document["updated_at"],
    }

async def login_user(
    email: str,
    password: str,
) -> dict[str, str]:
    user = await get_user_by_email(email)

    if not user:
        raise ValueError("Invalid email or password")

    if not user.get("is_active", False):
        raise ValueError("User account is inactive")

    password_hash = user.get("password_hash")

    if not password_hash:
        raise ValueError("Invalid email or password")

    if not verify_password(password, password_hash):
        raise ValueError("Invalid email or password")

    access_token = create_access_token(
        user_id=str(user["_id"]),
        role=user["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
