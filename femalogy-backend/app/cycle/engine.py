"""Cycle engine: works out cycle day, phase and next-period estimate.

Pure functions, no database. Everything here is an ESTIMATE and the app must
always present it that way (never as contraception).

Cycle length model (see docs/prediction-model.md for the full backtest):
Empirical Bayes. Her estimate is a blend of her own recent cycles and the
population average; the weight on her own data grows with every cycle she
logs. Before blending, a cycle about twice her usual length is treated as a
period that wasn't logged (split in two), and single odd cycles are clipped.
Parameters were fitted on, and the method validated against, the Marquette
fertility study data (159 women, 1,665 cycles with measured ovulation),
scored on held-out women only:
- next-period error 2.24 days on average vs 2.32 for a plain median
- with one unlogged period in her history: 2.12 days vs 6.21
- the 80% range really contains the next period 80% of the time

Other evidence (app/knowledge/sources.json):
- Mean cycle 29.3 days (Bull 2019, 600k cycles); luteal phase median 12-13
  days depending on how it's measured (Najmabadi 2020, Marquette data)
- Follicular phase drives most of the variation (Fehring 2006)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from itertools import pairwise
from statistics import median

DEFAULT_CYCLE_LENGTH = 28  # kept for reference; the model starts from POP_MEAN
DEFAULT_PERIOD_LENGTH = 5
# Ovulation = next period minus this. 13 beat 12 and 14 when predicting measured
# ovulation in the Marquette data (error 2.3 vs 2.6 days for 12).
DEFAULT_LUTEAL_LENGTH = 13

# Fitted on the Marquette data (mean over 5 cross-validation folds).
POP_MEAN = 29.3  # average cycle length across women
WITHIN_VAR = 9.08  # how much one woman's cycles vary month to month (days^2)
BETWEEN_VAR = 7.79  # how much women's own averages differ from each other (days^2)
POP_SD = 3.89  # spread of all cycles; used to clip odd cycles when history is short
RANGE_Z = 1.03  # calibrated so the predicted range holds the real date 80% of the time

MIN_CYCLE = 15  # anything shorter is probably a logging mistake, ignore it
MAX_CYCLE = 90
CYCLES_FOR_ESTIMATE = 6  # look back at most this many complete cycles
HIGH_VARIABILITY_RANGE = 9  # days between her shortest and longest recent cycle
NO_PERIOD_RED_FLAG_DAYS = 90


class Phase(StrEnum):
    MENSTRUAL = "menstrual"
    FOLLICULAR = "follicular"
    OVULATION = "ovulation"
    LUTEAL = "luteal"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CycleSettings:
    """What she told us at onboarding. Logged data overrides these."""

    avg_cycle_length: int | None = None
    avg_period_length: int | None = None
    luteal_length: int | None = None


@dataclass
class CycleStatus:
    today: date
    cycle_start: date
    cycle_day: int
    phase: Phase
    cycle_length_estimate: int
    period_length_estimate: int
    ovulation_day_estimate: int
    ovulation_date_estimate: date
    next_period_estimate: date
    days_until_next_period: int
    confidence: Confidence
    complete_cycles_logged: int
    next_period_earliest: date | None = None
    next_period_latest: date | None = None
    possible_missed_period: date | None = None  # ask her: did a period start around here?
    possible_missed_before: date | None = None  # start date of the period that ends that gap
    flags: list[str] = field(default_factory=list)


def cycle_lengths(period_starts: list[date]) -> list[int]:
    """Lengths of complete cycles from sorted period start dates, outliers dropped."""
    starts = sorted(set(period_starts))
    lengths = [(b - a).days for a, b in pairwise(starts)]
    return [n for n in lengths if MIN_CYCLE <= n <= MAX_CYCLE]


def split_missed(lengths: list[int], keep: frozenset[int] = frozenset()) -> tuple[list[float], int | None]:
    """A cycle about twice her usual length is most likely a period that wasn't
    logged. Count it as two cycles of half the length. Cycles she confirmed as
    real (indexes in `keep`) are left alone. Returns the cleaned lengths and
    the index of the last cycle that looked like a missed log."""
    out: list[float] = []
    last_missed = None
    for i, x in enumerate(lengths):
        others = [y for j, y in enumerate(lengths) if j != i]
        ref = median(others) if len(others) >= 2 else POP_MEAN
        if i not in keep and x >= 40 and 1.6 * ref <= x <= 2.4 * ref:
            out += [x / 2, x / 2]
            last_missed = i
        else:
            out.append(float(x))
    return out, last_missed


def _clip(h: list[float]) -> list[float]:
    """Limit how far one odd cycle can pull the estimate."""
    if len(h) >= 3:
        mid, spread = median(h), 2.5 * WITHIN_VAR ** 0.5
    else:
        mid, spread = POP_MEAN, 2.5 * POP_SD
    return [min(max(x, mid - spread), mid + spread) for x in h]


def _blend(lengths: list[int], settings: CycleSettings, keep: frozenset[int] = frozenset()) -> tuple[float, float]:
    """(estimate, predictive SD) for her next cycle length."""
    cleaned, _ = split_missed(lengths, keep)
    h = _clip(cleaned[-CYCLES_FOR_ESTIMATE:])
    if not h and settings.avg_cycle_length:
        h = [float(settings.avg_cycle_length)]  # her onboarding answer counts as one cycle
    n = len(h)
    if n == 0:
        return POP_MEAN, (WITHIN_VAR + BETWEEN_VAR) ** 0.5
    w = n * BETWEEN_VAR / (n * BETWEEN_VAR + WITHIN_VAR)
    est = w * (sum(h) / n) + (1 - w) * POP_MEAN
    post_var = 1 / (1 / BETWEEN_VAR + n / WITHIN_VAR)
    return est, (WITHIN_VAR + post_var) ** 0.5


def estimate_cycle_length(lengths: list[int], settings: CycleSettings) -> int:
    return round(_blend(lengths, settings)[0])


def estimate_confidence(lengths: list[int]) -> Confidence:
    recent = lengths[-CYCLES_FOR_ESTIMATE:]
    if len(recent) < 2:
        return Confidence.LOW
    spread = max(recent) - min(recent)
    if spread > HIGH_VARIABILITY_RANGE:
        return Confidence.LOW
    if len(recent) >= 3 and spread <= 4:
        return Confidence.HIGH
    return Confidence.MEDIUM


def phase_for_day(
    cycle_day: int, period_length: int, ovulation_day: int
) -> Phase:
    """Phase for a 1-based cycle day.

    Biologically the follicular phase starts on day 1 and overlaps the bleed.
    The app shows the bleed as its own 'menstrual' phase because that's what
    users care about, then 'follicular' for the rest of it.
    Ovulation is shown as a 3-day window around the estimated day.
    """
    if cycle_day <= period_length:
        return Phase.MENSTRUAL
    if ovulation_day - 1 <= cycle_day <= ovulation_day + 1:
        return Phase.OVULATION
    if cycle_day < ovulation_day - 1:
        return Phase.FOLLICULAR
    return Phase.LUTEAL


def compute_status(
    period_starts: list[date],
    today: date,
    settings: CycleSettings | None = None,
    period_lengths: list[int] | None = None,
    confirmed_gaps: set[date] | None = None,
) -> CycleStatus:
    """Main entry point. period_starts = every logged period start date."""
    settings = settings or CycleSettings()
    starts = sorted(d for d in set(period_starts) if d <= today)
    if not starts:
        raise ValueError("need at least one period start date on or before today")

    lengths = cycle_lengths(starts)
    # cycles she confirmed as real long cycles, by the start date that ends them
    ends = [b for a, b in pairwise(starts) if MIN_CYCLE <= (b - a).days <= MAX_CYCLE]
    keep = frozenset(i for i, b in enumerate(ends) if b in (confirmed_gaps or set()))
    est, sd = _blend(lengths, settings, keep)
    cycle_len = round(est)
    half_range = max(1, round(RANGE_Z * sd))

    if period_lengths:
        period_len = round(median(period_lengths[-CYCLES_FOR_ESTIMATE:]))
    else:
        period_len = settings.avg_period_length or DEFAULT_PERIOD_LENGTH
    period_len = max(2, min(period_len, 10))

    luteal = settings.luteal_length or DEFAULT_LUTEAL_LENGTH
    ovulation_day = cycle_len - luteal
    # very short cycles: ovulation can't land inside the bleed
    ovulation_day = max(ovulation_day, period_len + 2)

    cycle_start = starts[-1]
    cycle_day = (today - cycle_start).days + 1

    flags: list[str] = []
    if cycle_day > cycle_len:
        # period is due or late: she's still in luteal as far as we know
        phase = Phase.LUTEAL
        if cycle_day > cycle_len + 1:  # day cycle_len + 1 is the due day itself
            flags.append("period_late")
    else:
        phase = phase_for_day(cycle_day, period_len, ovulation_day)

    if cycle_day > NO_PERIOD_RED_FLAG_DAYS:
        flags.append("no_period_90_days")

    cleaned = [round(x) for x in split_missed(lengths, keep)[0]]
    confidence = estimate_confidence(cleaned)
    recent = cleaned[-CYCLES_FOR_ESTIMATE:]
    if len(recent) >= 2 and max(recent) - min(recent) > HIGH_VARIABILITY_RANGE:
        flags.append("high_variability")
    if len(lengths) < 2:
        flags.append("needs_more_data")

    next_period = cycle_start + timedelta(days=cycle_len)
    earliest = next_period - timedelta(days=half_range)
    latest = next_period + timedelta(days=half_range)
    if next_period < today:
        next_period = today  # overdue: best guess is "any day now"
    earliest = max(earliest, today)
    latest = max(latest, today)

    # a gap that looks like an unlogged period: point at roughly when it was
    possible_missed = None
    missed_before = None
    _, missed_i = split_missed(lengths, keep)
    if missed_i is not None:
        b = ends[missed_i]
        possible_missed = b - timedelta(days=lengths[missed_i] // 2)
        missed_before = b
        flags.append("possible_missed_period")
        confidence = Confidence.LOW  # until she tells us what happened in that gap

    return CycleStatus(
        today=today,
        cycle_start=cycle_start,
        cycle_day=cycle_day,
        phase=phase,
        cycle_length_estimate=cycle_len,
        period_length_estimate=period_len,
        ovulation_day_estimate=ovulation_day,
        ovulation_date_estimate=cycle_start + timedelta(days=ovulation_day - 1),
        next_period_estimate=next_period,
        days_until_next_period=(next_period - today).days,
        confidence=confidence,
        complete_cycles_logged=len(lengths),
        next_period_earliest=earliest,
        next_period_latest=latest,
        possible_missed_period=possible_missed,
        possible_missed_before=missed_before,
        flags=flags,
    )


def phase_calendar(
    status: CycleStatus, days_ahead: int = 35
) -> list[tuple[date, Phase]]:
    """Predicted phase for each upcoming day, for the calendar view.

    Day 0 always matches compute_status (same phase as /today). The current
    cycle runs until the next period estimate; if that's today or already
    passed (due/late), predicted cycles start from tomorrow.
    """
    cycle_len = status.cycle_length_estimate
    anchor = status.next_period_estimate
    if anchor <= status.today:
        anchor = status.today + timedelta(days=1)

    out: list[tuple[date, Phase]] = [(status.today, status.phase)]
    for i in range(1, days_ahead):
        d = status.today + timedelta(days=i)
        if d < anchor:
            day = (d - status.cycle_start).days + 1
            phase = (
                Phase.LUTEAL if day > cycle_len
                else phase_for_day(day, status.period_length_estimate, status.ovulation_day_estimate)
            )
        else:
            day = (d - anchor).days % cycle_len + 1
            phase = phase_for_day(day, status.period_length_estimate, status.ovulation_day_estimate)
        out.append((d, phase))
    return out
