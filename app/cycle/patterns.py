"""Personal patterns: how HER mood, energy, sleep and symptoms shift by phase.

Pure functions, no database. The rules are deliberately strict so the app
never claims a pattern from one odd month:
- each check-in is placed in a cycle using the real length of that cycle
  (or the current estimate for the cycle she's in now)
- a phase needs check-ins from at least MIN_CYCLES different cycles
- a metric pattern is only her lowest or highest phase, clearly apart from the
  rest of her cycle and from the next-closest phase, AND the same direction
  in at least MIN_CYCLES cycles
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date
from statistics import mean

from app.cycle.engine import DEFAULT_LUTEAL_LENGTH, MAX_CYCLE, MIN_CYCLE, Phase, phase_for_day

METRICS = ("mood", "energy", "sleep_quality")
MIN_CYCLES = 2  # a pattern must show up in at least this many cycles
MIN_CHECKINS_PER_PHASE = 3
MIN_GAP = 0.6  # points on the 1-5 scale away from the rest of her cycle
SEPARATION = 0.4  # and this far from her next-closest phase
SYMPTOM_MIN_SHARE = 0.5  # logged on at least half her check-ins in that phase
SYMPTOM_MIN_LIFT = 2.0  # and at least twice as often as in her other phases


@dataclass
class CheckinPoint:
    day: date
    mood: int | None = None
    energy: int | None = None
    sleep_quality: int | None = None
    symptoms: list[str] = field(default_factory=list)


@dataclass
class Insight:
    id: str
    kind: str  # "metric" or "symptom"
    key: str  # metric name or symptom id
    phase: Phase
    direction: str  # "lower", "higher" or "often"
    phase_value: float
    baseline: float
    cycles: int
    checkins: int


@dataclass
class PatternReport:
    status: str  # "learning" or "ready"
    cycles_with_checkins: int
    checkins_used: int
    cycles_needed: int
    insights: list[Insight]


def _placed(
    starts: list[date], current_len: int, period_len: int, checkins: list[CheckinPoint]
) -> list[tuple[int, Phase, CheckinPoint]]:
    """(cycle index, phase, check-in) for every check-in that falls in a known cycle."""
    out = []
    for c in checkins:
        i = bisect_right(starts, c.day) - 1
        if i < 0:
            continue  # before her first logged period
        if i + 1 < len(starts):
            length = (starts[i + 1] - starts[i]).days
            if not MIN_CYCLE <= length <= MAX_CYCLE:
                continue  # probably a logging mistake, skip that cycle
        else:
            length = current_len
        day = (c.day - starts[i]).days + 1
        if day > length:
            phase = Phase.LUTEAL  # late period: still luteal as far as we know
        else:
            ovulation = max(length - DEFAULT_LUTEAL_LENGTH, period_len + 2)
            phase = phase_for_day(day, period_len, ovulation)
        out.append((i, phase, c))
    return out


def find_patterns(
    period_starts: list[date], current_cycle_length: int, period_length: int, checkins: list[CheckinPoint]
) -> PatternReport:
    starts = sorted(set(period_starts))
    placed = _placed(starts, current_cycle_length, period_length, checkins)
    cycles_seen = {i for i, _, _ in placed}
    if len(cycles_seen) < MIN_CYCLES:
        return PatternReport("learning", len(cycles_seen), len(placed), MIN_CYCLES, [])

    insights: list[Insight] = []

    for metric in METRICS:
        rows = [(i, p, getattr(c, metric)) for i, p, c in placed if getattr(c, metric) is not None]
        if len(rows) < MIN_CHECKINS_PER_PHASE * 2:
            continue
        # phases with enough data from enough different cycles
        usable = {}
        for phase in Phase:
            vals = [(i, v) for i, p, v in rows if p == phase]
            if len(vals) >= MIN_CHECKINS_PER_PHASE and len({i for i, _ in vals}) >= MIN_CYCLES:
                usable[phase] = vals
        if len(usable) < 2:
            continue
        means = {ph: mean(v for _, v in vals) for ph, vals in usable.items()}
        ranked = sorted(means, key=means.get)
        # only her lowest and highest phase can stand out, and only if it is clearly
        # apart from the next-closest phase (so one low phase doesn't make all the others "high")
        for phase, neighbour, direction in ((ranked[0], ranked[1], "lower"), (ranked[-1], ranked[-2], "higher")):
            if abs(means[phase] - means[neighbour]) < SEPARATION:
                continue
            rest = [v for _, p, v in rows if p != phase]
            baseline = mean(rest)
            gap = means[phase] - baseline
            if abs(gap) < MIN_GAP or (gap < 0) != (direction == "lower"):
                continue
            # the same direction has to show up cycle by cycle, not just on average
            cycles = {i for i, _ in usable[phase]}
            same_way = 0
            for cyc in cycles:
                here = [v for i, v in usable[phase] if i == cyc]
                others = [v for i, p, v in rows if i == cyc and p != phase] or rest
                if (mean(here) - mean(others)) * gap > 0:
                    same_way += 1
            if same_way < MIN_CYCLES:
                continue
            insights.append(Insight(
                id=f"{metric}-{phase.value}", kind="metric", key=metric, phase=phase, direction=direction,
                phase_value=round(means[phase], 1), baseline=round(baseline, 1),
                cycles=same_way, checkins=len(usable[phase]),
            ))

    symptoms = {s for _, _, c in placed for s in c.symptoms}
    for symptom in sorted(symptoms):
        for phase in Phase:
            here = [(i, symptom in c.symptoms) for i, p, c in placed if p == phase]
            other = [symptom in c.symptoms for _, p, c in placed if p != phase]
            if len(here) < MIN_CHECKINS_PER_PHASE:
                continue
            share = sum(h for _, h in here) / len(here)
            other_share = sum(other) / len(other) if other else 0.0
            cycles = {i for i, h in here if h}
            if share < SYMPTOM_MIN_SHARE or len(cycles) < MIN_CYCLES:
                continue
            if other_share and share < other_share * SYMPTOM_MIN_LIFT:
                continue
            insights.append(Insight(
                id=f"symptom-{symptom}-{phase.value}", kind="symptom", key=symptom, phase=phase,
                direction="often", phase_value=round(share, 2), baseline=round(other_share, 2),
                cycles=len(cycles), checkins=len(here),
            ))

    return PatternReport("ready", len(cycles_seen), len(placed), MIN_CYCLES, insights)
