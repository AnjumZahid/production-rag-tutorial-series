from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.api.auth_schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.api.dependencies import (
    RequestIdentity,
    get_database_session_dependency,
    get_request_identity,
)
from backend.app.auth.service import (
    AuthResult,
    AuthUser,
    AuthenticationService,
)
from backend.app.core.config import (
    settings,
)
from backend.app.rate_limiting.dependencies import (
    require_ip_rate_limit,
)


router = APIRouter(
    prefix=settings.api_prefix,
    tags=["Authentication"],
)


# =============================================================
# Step 35B — endpoint-specific authentication limits
# =============================================================


register_rate_limit = (
    require_ip_rate_limit(
        scope="auth-register",
        limit=(
            settings
            .rate_limit_register_requests
        ),
        window_seconds=(
            settings
            .rate_limit_register_window_seconds
        ),
    )
)


login_rate_limit = (
    require_ip_rate_limit(
        scope="auth-login",
        limit=(
            settings
            .rate_limit_login_requests
        ),
        window_seconds=(
            settings
            .rate_limit_login_window_seconds
        ),
    )
)


refresh_rate_limit = (
    require_ip_rate_limit(
        scope="auth-refresh",
        limit=(
            settings
            .rate_limit_refresh_requests
        ),
        window_seconds=(
            settings
            .rate_limit_refresh_window_seconds
        ),
    )
)


# =============================================================
# Register
# =============================================================


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
    dependencies=[
        Depends(
            register_rate_limit
        ),
    ],
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> TokenResponse:
    service = AuthenticationService(
        session=session
    )

    result = await service.register(
        organization_name=(
            request.organization_name
        ),
        email=str(
            request.email
        ),
        password=request.password,
        full_name=request.full_name,
    )

    return token_response_from_result(
        result
    )


# =============================================================
# Login
# =============================================================


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(
            login_rate_limit
        ),
    ],
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> TokenResponse:
    service = AuthenticationService(
        session=session
    )

    result = await service.login(
        email=str(
            request.email
        ),
        password=request.password,
    )

    return token_response_from_result(
        result
    )


# =============================================================
# Refresh
# =============================================================


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    dependencies=[
        Depends(
            refresh_rate_limit
        ),
    ],
)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> TokenResponse:
    service = AuthenticationService(
        session=session
    )

    result = await service.refresh(
        refresh_token=(
            request.refresh_token
        ),
    )

    return token_response_from_result(
        result
    )


# =============================================================
# Logout
# =============================================================


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
)
async def logout(
    request: LogoutRequest,
    identity: RequestIdentity = Depends(
        get_request_identity
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> MessageResponse:
    service = AuthenticationService(
        session=session
    )

    await service.logout(
        refresh_token=(
            request.refresh_token
        ),
        user_id=identity.user_id,
        organization_id=(
            identity.organization_id
        ),
    )

    return MessageResponse(
        status="success",
        message=(
            "Logged out successfully."
        ),
    )


# =============================================================
# Current user
# =============================================================


@router.get(
    "/auth/me",
    response_model=UserResponse,
)
async def me(
    identity: RequestIdentity = Depends(
        get_request_identity
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> UserResponse:
    service = AuthenticationService(
        session=session
    )

    user = (
        await service.get_current_user(
            user_id=identity.user_id,
            organization_id=(
                identity.organization_id
            ),
        )
    )

    return user_response_from_auth_user(
        user
    )


# =============================================================
# Response helpers
# =============================================================


def token_response_from_result(
    result: AuthResult,
) -> TokenResponse:
    return TokenResponse(
        access_token=(
            result.access_token
        ),
        refresh_token=(
            result.refresh_token
        ),
        token_type=(
            result.token_type
        ),
        expires_in=(
            result.expires_in
        ),
        user=(
            user_response_from_auth_user(
                result.user
            )
        ),
    )


def user_response_from_auth_user(
    user: AuthUser,
) -> UserResponse:
    return UserResponse(
        id=user.id,
        organization_id=(
            user.organization_id
        ),
        organization_name=(
            user.organization_name
        ),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )