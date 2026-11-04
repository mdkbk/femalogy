from app.knowledge.loader import knowledge, sources, validate


def test_every_tip_is_cited():
    assert validate() == []


def test_all_four_phases_present():
    assert set(knowledge()["phases"]) == {"menstrual", "follicular", "ovulation", "luteal"}


def test_sources_have_doi():
    assert all(s["doi"].startswith("10.") for s in sources().values())
