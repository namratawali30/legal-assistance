from typing import Callable

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.security import (
    decode_access_token,
)
from app.repositories.user_repository import (
    get_user_by_id,
)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail=("Authentication credentials " "were not provided"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)

    except ValueError:
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail=("Invalid or expired token"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail=("Invalid authentication " "credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get(
        "is_active",
        False,
    ):
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail=("Invalid authentication " "credentials"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(
    required_role: str,
) -> Callable:
    async def role_checker(
        current_user: dict = Depends(get_current_user),
    ):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=(status.HTTP_403_FORBIDDEN),
                detail=("Insufficient permissions"),
            )

        return current_user

    return role_checker
