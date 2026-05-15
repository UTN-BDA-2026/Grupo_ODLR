"""Router registration tests.

Verifies that expected endpoint groups are exposed in OpenAPI.
"""

import os

from fastapi.testclient import TestClient

os.environ["DEBUG"] = "true"

from app.main import create_application


def test_users_routes_are_registered_in_openapi() -> None:
    """Users endpoints must be present in the API schema."""
    app = create_application()
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert any(path.startswith("/api/v1/users") for path in paths)
    assert any(path.startswith("/api/v1/auth") for path in paths)
