"""Cycle engine: works out cycle day, phase and next-period estimate.

Pure functions, no database. Everything here is an ESTIMATE and the app must
always present it that way (never as contraception).

Evidence behind the defaults (see app/knowledge/sources.json):
- Mean cycle 29.3 days, luteal 12.4 days (Bull 2019, 600k cycles)
- Luteal mean 11.7, median 12 days; luteal length shifts >3 days
  between cycles in 58.8% of women (Najmabadi 2020)
- Follicular phase drives most of the variation (Fehring 2006)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from itertools import pairwise
from statistics import median

DEFAULT_CYCLE_LENGTH = 28  # only used until she has logged real cycles
DEFAULT_PERIOD_LENGTH = 5
DEFAULT_LUTEAL_LENGTH = 12  # median luteal length (Najmabadi 2020)

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
    flags: list[str] = field(default_factory=list)


def cycle_lengths(period_starts: list[date]) -> list[int]:
    """Lengths of complete cycles from sorted period start dates, outliers dropped."""
    starts = sorted(set(period_starts))
    lengths = [(b - a).days for a, b in pairwise(starts)]
    return [n for n in lengths if MIN_CYCLE <= n <= MAX_CYCLE]


def estimate_cycle_length(lengths: list[int], settings: CycleSettings) -> int:
    recent = lengths[-CYCLES_FOR_ESTIMATE:]
    if recent:
        # median is robust to one odd month (illness, travel, stress)
        return round(median(recent))
    return settings.avg_cycle_length or DEFAULT_CYCLE_LENGTH


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
) -> CycleStatus:
    """Main entry point. period_starts = every logged period start date."""
    settings = settings or CycleSettings()
    starts = sorted(d for d in set(period_starts) if d <= today)
    if not starts:
        raise ValueError("need at least one period start date on or before today")

    lengths = cycle_lengths(starts)
    cycle_len = estimate_cycle_length(lengths, settings)

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
        # period is later than expected: she's still in luteal as far as we know
        flags.append("period_late")
        phase = Phase.LUTEAL
    else:
        phase = phase_for_day(cycle_day, period_len, ovulation_day)

    if cycle_day > NO_PERIOD_RED_FLAG_DAYS:
        flags.append("no_period_90_days")

    confidence = estimate_confidence(lengths)
    recent = lengths[-CYCLES_FOR_ESTIMATE:]
    if len(recent) >= 2 and max(recent) - min(recent) > HIGH_VARIABILITY_RANGE:
        flags.append("high_variability")
    if len(lengths) < 2:
        flags.append("needs_more_data")

    next_period = cycle_start + timedelta(days=cycle_len)
    if next_period < today:
        next_period = today  # overdue: best guess is "any day now"

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
        flags=flags,
    )


def phase_calendar(
    status: CycleStatus, days_ahead: int = 35
) -> list[tuple[date, Phase]]:
    """Predicted phase for each upcoming day, for the calendar view."""
    out: list[tuple[date, Phase]] = []
    for i in range(days_ahead):
        d = status.today + timedelta(days=i)
        day = (d - status.cycle_start).days % status.cycle_length_estimate + 1
        out.append(
            (d, phase_for_day(day, status.period_length_estimate, status.ovulation_day_estimate))
        )
    return out
