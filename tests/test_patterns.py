from datetime import date, timedelta

from app.cycle.engine import Phase
from app.cycle.patterns import CheckinPoint, find_patterns

D0 = date(2026, 1, 1)
STARTS = [D0 + timedelta(days=28 * i) for i in range(4)]  # 3 complete cycles + current


def checkins(cycles=3, low_luteal_energy=True, every=2):
    out = []
    for c in range(cycles):
        for day in range(1, 29, every):
            d = STARTS[c] + timedelta(days=day - 1)
            luteal = day >= 18
            energy = 2 if (luteal and low_luteal_energy) else 4
            out.append(CheckinPoint(d, mood=3, energy=energy, sleep_quality=3,
                                    symptoms=["cravings"] if day >= 19 else []))
    return out


def test_learning_until_two_cycles():
    r = find_patterns(STARTS, 28, 5, checkins(cycles=1))
    assert r.status == "learning"
    assert r.insights == []
    assert r.cycles_with_checkins == 1


def test_finds_consistent_luteal_energy_dip():
    r = find_patterns(STARTS, 28, 5, checkins())
    assert r.status == "ready"
    ids = {i.id for i in r.insights}
    assert "energy-luteal" in ids
    dip = next(i for i in r.insights if i.id == "energy-luteal")
    assert dip.direction == "lower" and dip.phase == Phase.LUTEAL and dip.cycles >= 2
    # flat metrics never produce a pattern
    assert not any(i.key in ("mood", "sleep_quality") for i in r.insights)
    # one low phase must not make every other phase look "higher"
    assert not any(i.key == "energy" and i.direction == "higher" for i in r.insights)


def test_symptom_pattern():
    r = find_patterns(STARTS, 28, 5, checkins())
    assert "symptom-cravings-luteal" in {i.id for i in r.insights}


def test_one_odd_cycle_is_not_a_pattern():
    pts = checkins(cycles=3, low_luteal_energy=False)
    # only the first cycle has a low luteal phase
    pts = [
        CheckinPoint(p.day, p.mood, 1 if (p.day < STARTS[1] and (p.day - STARTS[0]).days >= 17) else p.energy,
                     p.sleep_quality, [])
        for p in pts
    ]
    r = find_patterns(STARTS, 28, 5, pts)
    assert not any(i.key == "energy" for i in r.insights)


def test_checkins_before_first_period_ignored():
    early = [CheckinPoint(D0 - timedelta(days=3), energy=1)]
    r = find_patterns(STARTS, 28, 5, early)
    assert r.checkins_used == 0


def test_real_peak_is_found():
    pts = []
    for c in range(3):
        for day in range(1, 29):
            d = STARTS[c] + timedelta(days=day - 1)
            energy = 5 if 6 <= day <= 14 else 3  # follicular high, rest flat
            pts.append(CheckinPoint(d, energy=energy))
    r = find_patterns(STARTS, 28, 5, pts)
    assert [(i.key, i.phase, i.direction) for i in r.insights] == [("energy", Phase.FOLLICULAR, "higher")]
