import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConflictException

os.environ["DEBUG"] = "true"

from app.main import create_application
from app.schemas.user import UserResponse
from app.services.user_service import user_service


@pytest.fixture
def client():
    app = create_application()
    return TestClient(app)


class TestUsersEndpoint:
    def test_create_user_returns_201(self, client):
        response_model = UserResponse(
            id="507f1f77bcf86cd799439011",
            email="user@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch.object(
            user_service, "create_user", AsyncMock(return_value=response_model)
        ) as mock_create_user:
            response = client.post(
                "/api/v1/users/",
                json={
                    "email": "user@example.com",
                    "username": "testuser",
                    "full_name": "Test User",
                    "password": "plain-password",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "507f1f77bcf86cd799439011"
        assert data["email"] == "user@example.com"
        mock_create_user.assert_awaited_once()

    def test_create_user_returns_409_for_conflict(self, client):
        with patch.object(
            user_service,
            "create_user",
            AsyncMock(side_effect=ConflictException("Email already registered")),
        ):
            response = client.post(
                "/api/v1/users/",
                json={
                    "email": "user@example.com",
                    "username": "testuser",
                    "full_name": "Test User",
                    "password": "plain-password",
                },
            )

        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered"
