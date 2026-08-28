"""Test fixtures: isolated in-memory database and authenticated client."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Forced (not setdefault) so a developer's local .env can never leak into the suite:
# tests must never reach a real database or a paid API.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret-key-for-gold-queen-api"
os.environ["GEMINI_API_KEY"] = ""
os.environ["PLUGGY_CLIENT_ID"] = ""
os.environ["PLUGGY_CLIENT_SECRET"] = ""

from app.core.database import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_client")
def auth_client_fixture(client: TestClient) -> TestClient:
    """A client already carrying a valid bearer token."""
    client.post(
        "/v1/auth/register",
        json={
            "email": "knight@goldqueen.dev",
            "display_name": "Test Knight",
            "password": "KnightDemo123!",
        },
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "knight@goldqueen.dev", "password": "KnightDemo123!"},
    )
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
