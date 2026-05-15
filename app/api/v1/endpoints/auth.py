"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import UnauthorizedException
from app.db.database import get_db_session
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService, auth_service

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    """Dependency provider for the authentication service."""
    return auth_service


async def get_current_user(
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Resolve the current user from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await service.get_current_user(session, credentials.credentials)
    except UnauthorizedException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user",
    description="Authenticate with username or email and return a bearer token",
)
async def login_for_access_token(
    login_data: LoginRequest,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    """Authenticate a user from a JSON body and issue an access token."""
    try:
        return await service.login(
            session, login_data.identifier, login_data.password
        )
    except UnauthorizedException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Return the authenticated user resolved from the bearer token",
)
async def read_current_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Return the current authenticated user."""
    return current_user
