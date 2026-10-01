from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import bcrypt
from jose import JWTError, jwt

from app.config import settings

BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(
    password: str,
) -> bytes:
    if not isinstance(password, str):
        raise ValueError("Password must be a string.")

    encoded = password.encode("utf-8")

    if len(encoded) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password exceeds the supported length.")

    return encoded


def hash_password(
    password: str,
) -> str:
    password_bytes = _password_bytes(password)

    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(
        password_bytes,
        salt,
    )

    return hashed_password.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        password_bytes = _password_bytes(plain_password)

        if not isinstance(
            hashed_password,
            str,
        ):
            return False

        hashed_bytes = hashed_password.encode("utf-8")

        return bcrypt.checkpw(
            password_bytes,
            hashed_bytes,
        )

    except (
        ValueError,
        TypeError,
    ):
        # Invalid input or corrupted stored password hash
        # is an authentication failure, not a server error.
        return False


def create_access_token(
    user_id: str,
    role: str,
) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid user ID is required.")

    now = datetime.now(timezone.utc)

    expire = now + timedelta(minutes=(settings.access_token_expire_minutes))

    payload = {
        "sub": user_id,
        # Keep this claim for compatibility, but
        # authorization must continue to use the
        # current MongoDB user record.
        "role": role,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=(settings.jwt_algorithm),
    )


def decode_access_token(
    token: str,
) -> dict:
    if not isinstance(token, str) or not token.strip():
        raise ValueError("Invalid or expired token")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )

    except (
        JWTError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError("Invalid or expired token") from exc

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Invalid token payload")

    return payload


# =========================================================
# REFRESH TOKENS
# =========================================================


REFRESH_TOKEN_BYTES = 48


def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    """
    SHA-256 hash of the refresh token for server-side storage.
    Only the hash is persisted — the plaintext token is returned
    to the client exactly once at creation time.
    """
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
