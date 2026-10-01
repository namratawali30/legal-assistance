from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone

from app.database import database
from app.db.collections import (
    USERS_COLLECTION,
    REFRESH_TOKENS_COLLECTION,
)

users_collection = database[USERS_COLLECTION]
refresh_tokens_collection = database[REFRESH_TOKENS_COLLECTION]


def normalize_email(
    email: str,
) -> str:
    return email.strip().lower()


async def get_user_by_email(
    email: str,
) -> dict[str, Any] | None:
    normalized_email = normalize_email(email)

    return await users_collection.find_one({"email": normalized_email})


async def get_user_by_id(
    user_id: str,
) -> dict[str, Any] | None:
    try:
        object_id = ObjectId(user_id)

    except (
        InvalidId,
        TypeError,
    ):
        return None

    return await users_collection.find_one({"_id": object_id})


async def create_user(
    user_data: dict[str, Any],
):
    result = await users_collection.insert_one(user_data)

    return result.inserted_id


# =========================================================
# REFRESH TOKEN REPOSITORY
# =========================================================


async def store_refresh_token(
    token_hash: str,
    user_id: str,
    expires_at: datetime,
) -> None:
    """Store a hashed refresh token linked to a user."""
    await refresh_tokens_collection.insert_one({
        "token_hash": token_hash,
        "user_id": user_id,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })


async def find_refresh_token(
    token_hash: str,
) -> dict[str, Any] | None:
    """Find a non-expired refresh token by its hash."""
    return await refresh_tokens_collection.find_one({
        "token_hash": token_hash,
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })


async def delete_refresh_token(
    token_hash: str,
) -> bool:
    """Revoke a specific refresh token."""
    result = await refresh_tokens_collection.delete_one({
        "token_hash": token_hash,
    })
    return result.deleted_count > 0


async def delete_all_user_refresh_tokens(
    user_id: str,
) -> int:
    """Revoke all refresh tokens for a user (e.g. on logout)."""
    result = await refresh_tokens_collection.delete_many({
        "user_id": user_id,
    })
    return result.deleted_count


async def cleanup_expired_refresh_tokens() -> int:
    """Remove expired refresh tokens from the database."""
    result = await refresh_tokens_collection.delete_many({
        "expires_at": {"$lte": datetime.now(timezone.utc)},
    })
    return result.deleted_count

