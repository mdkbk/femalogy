import os

from cryptography.fernet import Fernet

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test.db")
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/auth/register", json={"email": "test@example.com", "password": "supersecret1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
