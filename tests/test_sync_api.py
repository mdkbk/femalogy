from datetime import date, timedelta


def _seed(client, auth, low_energy=True):
    today = date.today()
    starts = [today - timedelta(days=28 * k + 10) for k in (3, 2, 1, 0)]
    for s in starts:
        r = client.post("/periods", headers=auth, json={"start_date": str(s), "end_date": str(s + timedelta(days=4))})
        assert r.status_code == 201
    for s in starts[:3]:
        for day in range(1, 29, 2):
            d = s + timedelta(days=day - 1)
            body = {"day": str(d), "mood": 3, "energy": 2 if (day >= 18 and low_energy) else 4, "sleep_quality": 3}
            assert client.put("/checkins", headers=auth, json=body).status_code == 200
    return today


def test_sync_learning_state(client, auth):
    client.post("/periods", headers=auth, json={"start_date": str(date.today() - timedelta(days=3))})
    r = client.get("/sync", headers=auth)
    assert r.status_code == 200
    s = r.json()
    assert s["personal_status"] == "learning"
    assert [a["id"] for a in s["areas"]] == ["movement", "food", "sleep", "mood", "body"]
    assert sum(len(a["tips"]) for a in s["areas"]) > 0
    assert all(t["sources"] for a in s["areas"] for t in a["tips"])


def test_sync_with_patterns_and_myths(client, auth):
    today = _seed(client, auth)
    ins = client.get("/insights", headers=auth).json()
    assert ins["status"] == "ready"
    assert any(i["id"] == "energy-luteal" for i in ins["insights"])
    # look at a luteal day of the current cycle: start was 10 days ago, so day 22 is in 11 days
    on = str(today + timedelta(days=11))
    s = client.get("/sync", headers=auth, params={"on": str(today)}).json()
    assert s["phase"] in ("follicular", "ovulation")
    s = client.get("/sync", headers=auth, params={"on": on}).json()
    assert s["phase"] == "luteal"
    movement = next(a for a in s["areas"] if a["id"] == "movement")
    assert any(p["id"] == "energy-luteal" for p in movement["personal"])
    assert any(m["id"] == "myth-phase-training" for m in movement["myths"])
    food = next(a for a in s["areas"] if a["id"] == "food")
    assert any(m["id"] == "myth-cravings-willpower" for m in food["myths"])


def test_plan_blocks(client, auth):
    _seed(client, auth)
    p = client.get("/plan", headers=auth, params={"days": 56}).json()
    blocks = p["blocks"]
    assert sum(b["days"] for b in blocks) == 56
    for a, b in zip(blocks, blocks[1:], strict=False):
        assert a["phase"] != b["phase"]
    assert blocks[0]["is_prediction"] is False
    luteal = [b for b in blocks if b["phase"] == "luteal"]
    assert luteal and any(i["id"] == "energy-luteal" for i in luteal[0]["personal"])


def test_myths_public_and_cited(client):
    r = client.get("/myths")
    assert r.status_code == 200
    assert len(r.json()) >= 4
    assert all(m["sources"] for m in r.json())


def test_sync_needs_period(client, auth):
    assert client.get("/sync", headers=auth).status_code == 409
