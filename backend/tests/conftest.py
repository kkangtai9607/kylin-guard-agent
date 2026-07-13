from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.security import hash_password
from backend.app.db.models import Base, Role, User
from backend.app.db.session import get_db
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def isolate_llm_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test suite deterministic even when the developer configured a real LLM."""
    for name in (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def db_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        roles = [Role(name=name) for name in ("admin", "operator", "approver", "auditor")]
        db.add(
            User(username="admin", password_hash=hash_password("StrongPassword123!"), roles=roles)
        )
        db.add(
            User(
                username="operator",
                password_hash=hash_password("StrongPassword123!"),
                roles=[roles[1]],
            )
        )
        db.add(
            User(
                username="approver",
                password_hash=hash_password("StrongPassword123!"),
                roles=[roles[2]],
            )
        )
        db.commit()
    return factory


@pytest.fixture
def client(db_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_db() -> Generator[Session, None, None]:
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}
