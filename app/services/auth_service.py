"""Authentication service."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserResponse


class AuthService:
    """Business logic for authentication and token-based identity."""

    collection_name = "users"

    def _get_repository(self, session: AsyncIOMotorDatabase) -> UserRepository:
        return UserRepository(session)

    def _to_response(self, document: UserDocument) -> UserResponse:
        return UserResponse(
            id=document.id,
            email=document.email,
            username=document.username,
            full_name=document.full_name,
            is_active=document.is_active,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def authenticate_user(
        self, session: AsyncIOMotorDatabase, identifier: str, password: str
    ) -> UserResponse:
        """Validate credentials using username or email."""
        repository = self._get_repository(session)
        document = await repository.get_by_identifier(identifier)

        if document is None or not verify_password(password, document.hashed_password):
            raise UnauthorizedException("Incorrect username/email or password")

        if not document.is_active:
            raise UnauthorizedException("Inactive user")

        return self._to_response(document)

    async def login(
        self, session: AsyncIOMotorDatabase, identifier: str, password: str
    ) -> Token:
        """Authenticate a user and return a bearer token."""
        user = await self.authenticate_user(session, identifier, password)
        return Token(access_token=create_access_token(user.id))

    async def get_current_user(
        self, session: AsyncIOMotorDatabase, token: str
    ) -> UserResponse:
        """Resolve a bearer token into the authenticated user."""
        payload = decode_access_token(token)
        repository = self._get_repository(session)
        document = await repository.get_by_id(payload["sub"])
        if document is None:
            raise UnauthorizedException("User not found for token")

        if not document.is_active:
            raise UnauthorizedException("Inactive user")

        return self._to_response(document)


auth_service = AuthService()
