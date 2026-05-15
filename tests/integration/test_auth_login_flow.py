import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

os.environ["DEBUG"] = "true"

from app.db.database import get_db_session
from app.main import create_application


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["auth_integration_test"]


@pytest.fixture
def client(mock_db):
    async def override_get_db_session():
        yield mock_db

    with patch("app.main.db.connect", AsyncMock()), patch(
        "app.main.db.disconnect", AsyncMock()
    ):
        app = create_application()
        app.dependency_overrides[get_db_session] = override_get_db_session

        with TestClient(app) as test_client:
            yield test_client


def test_login_and_me_end_to_end(client):
    create_response = client.post(
        "/api/v1/users/",
        json={
            "email": "user@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "plain-password",
        },
    )

    assert create_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testuser", "password": "plain-password"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"
