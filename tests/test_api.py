from datetime import date, timedelta

from sqlalchemy import text

from app.db import engine


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client):
    r = client.post("/auth/register", json={"email": "A@x.com", "password": "password123"})
    assert r.status_code == 201
    assert client.post("/auth/register", json={"email": "a@x.com", "password": "password123"}).status_code == 409
    r = client.post("/auth/login", data={"username": "a@x.com", "password": "password123"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/me", headers=h).json()["email"] == "a@x.com"
    assert client.post("/auth/login", data={"username": "a@x.com", "password": "nope-nope"}).status_code == 401


def test_requires_auth(client):
    assert client.get("/today").status_code == 401


def test_today_flow(client, auth):
    assert client.get("/today", headers=auth).status_code == 409
    client.put("/me", headers=auth, json={"avg_cycle_length": 28})
    start = date.today() - timedelta(days=21)
    assert client.post("/periods", headers=auth, json={"start_date": str(start)}).status_code == 201
    assert client.post("/periods", headers=auth, json={"start_date": str(start)}).status_code == 409
    body = client.get("/today", headers=auth).json()
    assert body["cycle_day"] == 22
    assert body["phase"] == "luteal"
    assert body["is_estimate"] is True
    assert body["guide"]["tips"], "phase guide should have tips"
    assert all(t["sources"] for t in body["guide"]["tips"])
    assert body["guide"]["tips"][0]["sources"][0]["url"].startswith("https://doi.org/")


def test_future_period_rejected(client, auth):
    r = client.post("/periods", headers=auth, json={"start_date": str(date.today() + timedelta(days=2))})
    assert r.status_code == 422


def test_guide_and_sources_public(client):
    assert client.get("/guide/menstrual").json()["phase"] == "menstrual"
    assert client.get("/guide/banana").status_code == 422
    assert len(client.get("/sources").json()) >= 15


def test_checkin_encrypts_notes_and_flags(client, auth):
    client.post("/periods", headers=auth, json={"start_date": str(date.today() - timedelta(days=1))})
    r = client.put("/checkins", headers=auth, json={
        "day": str(date.today()), "mood": 2, "energy": 2,
        "symptoms": ["cramps", "severe_pain"], "notes": "rough day",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["phase_at_checkin"] == "menstrual"
    assert [f["id"] for f in body["red_flags"]] == ["rf-pain"]
    with engine.connect() as c:
        raw = c.execute(text("select notes from checkins")).scalar()
    assert raw != "rough day"  # stored encrypted
    assert client.get("/checkins", headers=auth).json()[0]["notes"] == "rough day"
    # same day again = update, not duplicate
    client.put("/checkins", headers=auth, json={"day": str(date.today()), "mood": 4})
    assert len(client.get("/checkins", headers=auth).json()) == 1


def test_bad_symptom_rejected(client, auth):
    r = client.put("/checkins", headers=auth, json={"day": str(date.today()), "symptoms": ["zombie"]})
    assert r.status_code == 422


def test_delete_account_removes_data(client, auth):
    client.post("/periods", headers=auth, json={"start_date": str(date.today())})
    assert client.delete("/me", headers=auth).status_code == 204
    with engine.connect() as c:
        assert c.execute(text("select count(*) from periods")).scalar() == 0
