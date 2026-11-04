from datetime import date, timedelta

import pytest

from app.cycle.engine import (
    Confidence,
    CycleSettings,
    Phase,
    compute_status,
    cycle_lengths,
    phase_calendar,
)

D0 = date(2026, 1, 1)


def starts(*gaps, first=D0):
    out = [first]
    for g in gaps:
        out.append(out[-1] + timedelta(days=g))
    return out


def phase_on(day_number, history, settings=None):
    today = history[-1] + timedelta(days=day_number - 1)
    return compute_status(history, today, settings)


@pytest.mark.parametrize("length", [21, 28, 35])
def test_phases_line_up_for_regular_cycles(length):
    hist = starts(length, length, length)
    st = phase_on(1, hist)
    est = st.cycle_length_estimate
    # with 3 cycles the model mostly trusts her, but still leans a little toward the average
    assert min(length, 29) <= est <= max(length, 30)
    ov = est - 13
    assert st.ovulation_day_estimate == ov
    assert st.next_period_estimate == hist[-1] + timedelta(days=est)
    assert phase_on(1, hist).phase == Phase.MENSTRUAL
    assert phase_on(5, hist).phase == Phase.MENSTRUAL
    assert phase_on(ov, hist).phase == Phase.OVULATION
    assert phase_on(ov + 2, hist).phase == Phase.LUTEAL
    assert phase_on(est, hist).phase == Phase.LUTEAL


def test_follicular_exists_in_28_day_cycle():
    hist = starts(28, 28, 28)
    assert phase_on(8, hist).phase == Phase.FOLLICULAR


def test_single_period_uses_onboarding_answer_and_low_confidence():
    st = compute_status([D0], D0 + timedelta(days=9), CycleSettings(avg_cycle_length=32))
    assert 30 <= st.cycle_length_estimate <= 32  # her answer counts, blended with the average
    assert st.cycle_day == 10
    assert st.confidence == Confidence.LOW
    assert "needs_more_data" in st.flags


def test_median_ignores_one_odd_cycle():
    hist = starts(29, 29, 45, 29, 29)
    st = compute_status(hist, hist[-1])
    assert 29 <= st.cycle_length_estimate <= 30  # one odd month moves it a day at most


def test_logging_mistakes_are_dropped():
    assert cycle_lengths([D0, D0 + timedelta(days=3), D0 + timedelta(days=31)]) == [28]


def test_high_variability_flag_and_low_confidence():
    hist = starts(24, 38, 26, 36)
    st = compute_status(hist, hist[-1])
    assert "high_variability" in st.flags
    assert st.confidence == Confidence.LOW


def test_stable_cycles_get_high_confidence():
    st = compute_status(starts(28, 29, 28, 27), D0 + timedelta(days=200))
    assert st.confidence == Confidence.HIGH


def test_late_period_stays_luteal_and_flags():
    hist = starts(28, 28)
    st = compute_status(hist, hist[-1] + timedelta(days=33))
    assert st.phase == Phase.LUTEAL
    assert "period_late" in st.flags
    assert st.next_period_estimate == st.today
    assert st.days_until_next_period == 0


def test_no_period_90_days_red_flag():
    st = compute_status([D0], D0 + timedelta(days=95))
    assert "no_period_90_days" in st.flags


def test_very_short_cycle_ovulation_not_inside_period():
    hist = starts(16, 16)
    st = compute_status(hist, hist[-1], CycleSettings(avg_period_length=6))
    assert st.ovulation_day_estimate > st.period_length_estimate


def test_logged_period_lengths_used():
    hist = starts(28, 28)
    st = compute_status(hist, hist[-1], period_lengths=[7, 7, 6])
    assert st.period_length_estimate == 7
    day7 = compute_status(hist, hist[-1] + timedelta(days=6), period_lengths=[7, 7, 6])
    assert day7.phase == Phase.MENSTRUAL
    assert phase_on(7, hist).phase == Phase.FOLLICULAR  # default 5-day period without logs


def test_future_dates_ignored_and_empty_raises():
    with pytest.raises(ValueError):
        compute_status([D0 + timedelta(days=10)], D0)


def test_calendar_cycles_forward():
    hist = starts(28, 28)
    st = compute_status(hist, hist[-1])
    cal = phase_calendar(st, 56)
    assert cal[0][1] == Phase.MENSTRUAL
    assert cal[28][1] == Phase.MENSTRUAL
    assert {p for _, p in cal} == set(Phase)


def test_due_day_is_not_late_yet():
    hist = starts(28, 28)
    due = compute_status(hist, hist[-1] + timedelta(days=28))  # cycle day 29 = due day
    assert due.phase == Phase.LUTEAL
    assert "period_late" not in due.flags
    late = compute_status(hist, hist[-1] + timedelta(days=29))
    assert "period_late" in late.flags


def test_calendar_first_day_matches_status_even_when_late():
    hist = starts(28, 30)
    st = compute_status(hist, hist[-1] + timedelta(days=34))
    cal = phase_calendar(st, 40)
    assert cal[0] == (st.today, st.phase) == (st.today, Phase.LUTEAL)
    assert cal[1][1] == Phase.MENSTRUAL  # predicted period starts tomorrow
    for offset in (0, 5, 13, 20):  # normal mid-cycle days agree too
        s2 = compute_status(hist, hist[-1] + timedelta(days=offset))
        assert phase_calendar(s2, 1)[0][1] == s2.phase


# ---- prediction model (fitted and backtested on the Marquette data) ----

def test_unlogged_period_does_not_stretch_the_cycle():
    # her real case: Sep 1, then Oct 22 (51 days) - most likely a period in between wasn't logged
    st = compute_status([date(2026, 9, 1), date(2026, 10, 22)], date(2026, 11, 4))
    assert 26 <= st.cycle_length_estimate <= 30  # not 51
    assert "possible_missed_period" in st.flags
    assert st.confidence == Confidence.LOW
    assert date(2026, 9, 20) <= st.possible_missed_period <= date(2026, 10, 2)
    assert st.days_until_next_period < 20


def test_truly_long_cycles_are_not_split():
    hist = starts(44, 46, 45, 44)  # consistently ~45 days: that's her, not missed logs
    st = compute_status(hist, hist[-1])
    assert st.cycle_length_estimate >= 40
    assert "possible_missed_period" not in st.flags


def test_estimate_leans_on_population_until_she_has_data():
    one = compute_status(starts(34), D0 + timedelta(days=40))
    many = compute_status(starts(34, 34, 34, 34, 34, 34), D0 + timedelta(days=34 * 6 + 1))
    assert one.cycle_length_estimate < 34  # one cycle: pulled toward ~29
    assert many.cycle_length_estimate >= 33  # six steady cycles: mostly hers


def test_range_contains_estimate_and_narrows_with_data():
    few = compute_status(starts(29), D0 + timedelta(days=30))
    lots = compute_status(starts(29, 29, 29, 29, 29, 29), D0 + timedelta(days=29 * 6 + 1))
    for st in (few, lots):
        assert st.next_period_earliest <= st.next_period_estimate <= st.next_period_latest
    width = lambda s: (s.next_period_latest - s.next_period_earliest).days  # noqa: E731
    assert width(lots) <= width(few)


def test_ovulation_uses_13_day_luteal():
    hist = starts(29, 29)
    st = compute_status(hist, hist[-1])
    assert st.ovulation_day_estimate == st.cycle_length_estimate - 13


def test_confirmed_long_cycle_is_not_split():
    a, b = date(2026, 9, 1), date(2026, 10, 22)
    st = compute_status([a, b], date(2026, 11, 4), confirmed_gaps={b})
    assert "possible_missed_period" not in st.flags
    assert st.cycle_length_estimate > 32  # she said 51 days was real: it now counts (blended)
