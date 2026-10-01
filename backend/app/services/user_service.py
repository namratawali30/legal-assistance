from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.errors import (
    DuplicateKeyError,
)

from app.config import settings
from app.db.user_documents import (
    build_user_document,
)
from app.repositories.user_repository import (
    create_user,
    delete_all_user_refresh_tokens,
    delete_refresh_token,
    find_refresh_token,
    get_user_by_email,
    get_user_by_id,
    normalize_email,
    store_refresh_token,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
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

    user_id_str = str(user["_id"])

    access_token = create_access_token(
        user_id=user_id_str,
        role=user["role"],
    )

    # Generate and persist a refresh token
    refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    await store_refresh_token(
        token_hash=token_hash,
        user_id=user_id_str,
        expires_at=expires_at,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access_token(
    refresh_token: str,
) -> dict[str, str]:
    """
    Validate a refresh token, rotate it, and issue a
    new access token + refresh token pair.

    Rotation: the old refresh token is revoked and a
    new one is issued on every refresh. This limits
    the damage if a refresh token is leaked.
    """
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise ValueError("Invalid refresh token")

    old_hash = hash_refresh_token(refresh_token)
    stored = await find_refresh_token(old_hash)

    if not stored:
        raise ValueError("Invalid or expired refresh token")

    user_id = stored["user_id"]

    # Verify the user still exists and is active
    user = await get_user_by_id(user_id)

    if not user:
        await delete_refresh_token(old_hash)
        raise ValueError("Invalid refresh token")

    if not user.get("is_active", False):
        await delete_all_user_refresh_tokens(user_id)
        raise ValueError("Account is inactive")

    # Revoke the old refresh token (rotation)
    await delete_refresh_token(old_hash)

    # Issue new tokens
    access_token = create_access_token(
        user_id=user_id,
        role=user["role"],
    )

    new_refresh_token = generate_refresh_token()
    new_hash = hash_refresh_token(new_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )

    await store_refresh_token(
        token_hash=new_hash,
        user_id=user_id,
        expires_at=expires_at,
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


async def logout_user(
    refresh_token: str | None,
    user_id: str | None = None,
) -> None:
    """
    Revoke the refresh token. If a user_id is provided,
    revoke all refresh tokens for that user as a security
    measure.
    """
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        await delete_refresh_token(token_hash)

    if user_id:
        await delete_all_user_refresh_tokens(user_id)
