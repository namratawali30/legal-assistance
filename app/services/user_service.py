from typing import Any

from pymongo.errors import (
    DuplicateKeyError,
)

from app.db.user_documents import (
    build_user_document,
)
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    normalize_email,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

INVALID_LOGIN_MESSAGE = "Invalid email or password"

DUMMY_PASSWORD_HASH = hash_password(
    "unused-dummy-password-value"
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
    normalized_email = normalize_email(email)

    existing_user = await get_user_by_email(normalized_email)

    if existing_user:
        raise ValueError("Email is already registered")

    password_hash = hash_password(password)

    user_document = build_user_document(
        email=normalized_email,
        full_name=full_name,
        password_hash=password_hash,
    )

    try:
        user_id = await create_user(user_document)

    except DuplicateKeyError as exc:
        # The unique MongoDB email index is the
        # authoritative protection against two
        # simultaneous registration requests.
        raise ValueError("Email is already registered") from exc

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
    normalized_email = normalize_email(email)

    user = await get_user_by_email(normalized_email)

    if not user:
    # Perform one bcrypt verification even when the
    # account does not exist. This reduces the timing
    # difference between "unknown email" and
    # "incorrect password".
        verify_password(
            password,
            DUMMY_PASSWORD_HASH,
        )

        raise ValueError(
            INVALID_LOGIN_MESSAGE
        )

    password_hash = user.get("password_hash")

    if not password_hash or not verify_password(
        password,
        password_hash,
    ):
        raise ValueError(INVALID_LOGIN_MESSAGE)

    if not user.get(
        "is_active",
        False,
    ):
        raise ValueError(INVALID_LOGIN_MESSAGE)

    access_token = create_access_token(
        user_id=str(user["_id"]),
        role=user["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
