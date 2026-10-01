from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from app.services.rate_limiter import rate_limiter, get_client_ip
from app.core.dependencies import (
    get_current_user,
)
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.user_service import (
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    request: Request,
):
    ip = get_client_ip(request)
    await rate_limiter.check_rate_limit(f"auth_register:{ip}", max_requests=10, window_seconds=60)

    try:
        user = await register_user(
            email=user_data.email,
            full_name=user_data.full_name,
            password=user_data.password,
        )

        return user

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    user_data: UserLogin,
    request: Request,
):
    ip = get_client_ip(request)
    await rate_limiter.check_rate_limit(f"auth_login:{ip}", max_requests=15, window_seconds=60)

    try:
        return await login_user(
            email=user_data.email,
            password=user_data.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh(
    body: RefreshTokenRequest,
    request: Request,
):
    """
    Exchange a valid refresh token for a new access token
    and a rotated refresh token. The old refresh token is
    revoked immediately (rotation).
    """
    ip = get_client_ip(request)
    await rate_limiter.check_rate_limit(
        f"auth_refresh:{ip}",
        max_requests=30,
        window_seconds=60,
    )

    try:
        return await refresh_access_token(
            refresh_token=body.refresh_token,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Revoke all refresh tokens for the current user.
    The frontend should also clear any stored tokens.
    """
    user_id = str(current_user["_id"])

    # Try to extract refresh token from body if provided
    refresh_token = None
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except Exception:
        pass

    await logout_user(
        refresh_token=refresh_token,
        user_id=user_id,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: dict = Depends(get_current_user),
):
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_active": current_user["is_active"],
        "created_at": current_user["created_at"],
        "updated_at": current_user["updated_at"],
    }
