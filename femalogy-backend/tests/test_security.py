"""Sign-in security: cookie sessions, revocation, rate limits, CSRF, headers, data rights."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import LoginAttempt, UserSession
from tests.conftest import APP

WEB = {"Origin": "http://testserver"}  # what a browser on our own site sends
PW = "cycle-tracker-7"


def _web_signup(client, email="web@x.com"):
    r = client.post("/auth/register", headers=WEB, json={"email": email, "password": PW, "consent": True})
    assert r.status_code == 201
    return r


def test_web_gets_httponly_cookie_and_no_token(client):
    r = _web_signup(client)
    assert "access_token" not in r.json()  # nothing for page scripts to steal
    cookie = r.headers["set-cookie"].lower()
    assert "femalogy_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/me").json()["email"] == "web@x.com"  # the cookie alone signs her in


def test_database_never_holds_the_raw_token(client):
    r = client.post("/auth/register", headers=APP, json={"email": "t@x.com", "password": PW, "consent": True})
    token = r.json()["access_token"]
    with SessionLocal() as db:
        stored = [s.token_hash for s in db.scalars(select(UserSession))]
    assert token not in stored and len(stored[0]) == 64


def test_logout_revokes_the_session(client):
    _web_signup(client)
    assert client.post("/auth/logout", headers=WEB).status_code == 204
    assert client.get("/me").status_code == 401


def test_logout_everywhere(client):
    r = client.post("/auth/register", headers=APP, json={"email": "m@x.com", "password": PW, "consent": True})
    phone = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/auth/login", headers=APP, data={"username": "m@x.com", "password": PW})
    laptop = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/auth/logout-everywhere", headers=laptop).status_code == 204
    assert client.get("/me", headers=phone).status_code == 401


def test_cross_site_requests_are_blocked(client):
    _web_signup(client)
    evil = {"Origin": "https://evil.example"}
    assert client.post("/periods", headers=evil, json={"start_date": "2026-01-01"}).status_code == 403
    assert client.delete("/me", headers=evil).status_code == 403
    # cookie but no Origin and not same-origin: blocked too
    assert client.post("/periods", json={"start_date": "2026-01-01"}).status_code == 403
    # from our own page: fine
    assert client.post("/periods", headers=WEB, json={"start_date": "2026-01-01"}).status_code == 201


def _fail(client, email, n):
    for _ in range(n):
        r = client.post("/auth/login", headers=APP, data={"username": email, "password": "wrong-guess-1"})
        assert r.status_code == 401


def test_ten_wrong_tries_then_a_five_minute_pause(client):
    client.post("/auth/register", headers=APP, json={"email": "r@x.com", "password": PW, "consent": True})
    _fail(client, "r@x.com", 9)
    _fail(client, "r@x.com", 1)  # 10th wrong try still gets the normal message
    r = client.post("/auth/login", headers=APP, data={"username": "r@x.com", "password": PW})
    assert r.status_code == 429  # even the right password waits out the pause
    assert "5 minutes" in r.json()["detail"]


def test_pause_ends_after_five_minutes(client):
    from datetime import timedelta

    from app.models import LoginAttempt

    client.post("/auth/register", headers=APP, json={"email": "p@x.com", "password": PW, "consent": True})
    _fail(client, "p@x.com", 10)
    with SessionLocal() as db:  # pretend the tries happened 6 minutes ago
        for a in db.scalars(select(LoginAttempt).where(LoginAttempt.kind == "login")):
            a.created_at = a.created_at - timedelta(minutes=6)
        db.commit()
    r = client.post("/auth/login", headers=APP, data={"username": "p@x.com", "password": PW})
    assert r.status_code == 200


def test_successful_sign_in_resets_the_count(client):
    client.post("/auth/register", headers=APP, json={"email": "s@x.com", "password": PW, "consent": True})
    _fail(client, "s@x.com", 9)
    assert client.post("/auth/login", headers=APP, data={"username": "s@x.com", "password": PW}).status_code == 200
    _fail(client, "s@x.com", 9)  # a fresh 9: still no pause
    assert client.post("/auth/login", headers=APP, data={"username": "s@x.com", "password": PW}).status_code == 200


def test_attempts_store_no_emails_or_ips(client):
    client.post("/auth/login", headers=APP, data={"username": "who@x.com", "password": "whatever-1"})
    with SessionLocal() as db:
        a = db.scalars(select(LoginAttempt)).first()
    assert "who@x.com" not in (a.email_hash or "") and "testclient" not in a.ip_hash
    assert len(a.email_hash) == 64


def test_same_message_for_unknown_email_and_wrong_password(client):
    client.post("/auth/register", headers=APP, json={"email": "k@x.com", "password": PW, "consent": True})
    a = client.post("/auth/login", headers=APP, data={"username": "k@x.com", "password": "nope-nope-1"})
    b = client.post("/auth/login", headers=APP, data={"username": "nobody@x.com", "password": "nope-nope-1"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_weak_passwords_rejected(client):
    for pw in ("password123", "12345678", "aaaaaaaa"):
        r = client.post("/auth/register", headers=APP, json={"email": "w@x.com", "password": pw, "consent": True})
        assert r.status_code == 422, pw
    body = {"email": "samesame@x.com", "password": "samesame", "consent": True}
    r = client.post("/auth/register", headers=APP, json=body)
    assert r.status_code == 422


def test_security_headers_and_no_caching(client, auth):
    r = client.get("/me", headers=auth)
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_export_my_data(client, auth):
    client.post("/periods", headers=auth, json={"start_date": "2026-01-01"})
    client.put("/checkins", headers=auth, json={"day": "2026-01-02", "notes": "private note"})
    r = client.get("/me/export", headers=auth)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["profile"]["email"] == "test@example.com"
    assert data["periods"][0]["start_date"] == "2026-01-01"
    assert data["checkins"][0]["notes"] == "private note"


def test_delete_account_removes_sessions(client):
    _web_signup(client, "gone@x.com")
    assert client.delete("/me", headers=WEB).status_code == 204
    with SessionLocal() as db:
        assert db.scalars(select(UserSession)).first() is None
    assert client.get("/me").status_code == 401


def test_signup_needs_explicit_consent(client):
    r = client.post("/auth/register", headers=APP, json={"email": "c@x.com", "password": PW})
    assert r.status_code == 422 and "agree" in r.json()["detail"]
    r = client.post("/auth/register", headers=APP, json={"email": "c@x.com", "password": PW, "consent": True})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/me/export", headers=h).json()["profile"]["consented_at"]
