import os

from cryptography.fernet import Fernet

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test.db")
os.environ["SECRET_KEY"] = "test-secret-that-is-long-enough-for-hmac-keys"
os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

APP = {"X-Femalogy-Client": "app"}  # token in the body, like the mobile app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # every path in the tests is relative to /api
    with TestClient(app, base_url="http://testserver/api/") as c:
        yield c


@pytest.fixture()
def auth(client):
    body = {"email": "test@example.com", "password": "supersecret1", "consent": True}
    r = client.post("/auth/register", headers=APP, json=body)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
