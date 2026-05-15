"""
User endpoints.

Handles HTTP requests related to users.
Follows the Single Responsibility Principle.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import ConflictException, NotFoundException
from app.db.database import get_db_session
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import user_service

router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user account",
)
async def create_user(
    user_data: UserCreate, session: AsyncIOMotorDatabase = Depends(get_db_session)
) -> UserResponse:
    """
    Create a new user.

    Args:
        user_data: User creation data
        session: Database session

    Returns:
        Created user data
    """
    try:
        return await user_service.create_user(session, user_data)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List users",
    description="Get a list of all users with pagination",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
) -> List[UserResponse]:
    """
    List all users.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records
        session: Database session

    Returns:
        List of users
    """
    return await user_service.list_users(session, skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get a specific user by their ID",
)
async def get_user(
    user_id: str, session: AsyncIOMotorDatabase = Depends(get_db_session)
) -> UserResponse:
    """
    Get user by ID.

    Args:
        user_id: User ID
        session: Database session

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    try:
        return await user_service.get_user_by_id(session, user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update an existing user",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    session: AsyncIOMotorDatabase = Depends(get_db_session),
) -> UserResponse:
    """
    Update user.

    Args:
        user_id: User ID to update
        user_data: Update data
        session: Database session

    Returns:
        Updated user data
    """
    try:
        return await user_service.update_user(session, user_id, user_data)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user account",
)
async def delete_user(
    user_id: str, session: AsyncIOMotorDatabase = Depends(get_db_session)
) -> None:
    """
    Delete user.

    Args:
        user_id: User ID to delete
        session: Database session
    """
    try:
        await user_service.delete_user(session, user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
