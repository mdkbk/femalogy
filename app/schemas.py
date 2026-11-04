from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    avg_cycle_length: int | None = Field(default=None, ge=15, le=90)
    avg_period_length: int | None = Field(default=None, ge=1, le=14)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr


MAX_PERIOD_DAYS = 15


class PeriodIn(BaseModel):
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date can't be before start_date")
        if self.end_date and (self.end_date - self.start_date).days + 1 > MAX_PERIOD_DAYS:
            raise ValueError(f"a period can't last more than {MAX_PERIOD_DAYS} days; check the dates")
        return self


class PeriodOut(PeriodIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class Source(BaseModel):
    id: str
    authors: str
    year: int
    title: str
    journal: str
    doi: str
    url: str


class Tip(BaseModel):
    id: str
    category: str
    text: str
    grade: str
    sources: list[Source]


class PhaseGuide(BaseModel):
    phase: str
    title: str
    summary: str
    tips: list[Tip]


class RedFlag(BaseModel):
    id: str
    text: str


class TodayOut(BaseModel):
    date: date
    cycle_day: int
    phase: str
    phase_title: str
    is_estimate: bool = True
    cycle_length_estimate: int
    period_length_estimate: int
    ovulation_day_estimate: int
    ovulation_date_estimate: date
    next_period_estimate: date
    next_period_earliest: date
    next_period_latest: date
    possible_missed_period: date | None = None
    days_until_next_period: int
    confidence: str
    complete_cycles_logged: int
    flags: list[str]
    red_flags: list[RedFlag]
    guide: PhaseGuide
    disclaimer: str


SYMPTOMS = {
    "cramps", "headache", "bloating", "breast_tenderness", "acne", "back_pain",
    "fatigue", "cravings", "nausea", "very_heavy_bleeding", "severe_pain",
}


class CheckInIn(BaseModel):
    day: date
    mood: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    symptoms: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def known_symptoms(self):
        unknown = set(self.symptoms) - SYMPTOMS
        if unknown:
            raise ValueError(f"unknown symptoms: {sorted(unknown)}")
        return self


class CheckInOut(CheckInIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    phase_at_checkin: str | None
    red_flags: list[RedFlag] = []


class Myth(BaseModel):
    id: str
    claim: str
    verdict: str
    verdict_label: str
    text: str
    area: str
    phases: list[str]
    sources: list[Source]


class InsightOut(BaseModel):
    id: str
    kind: str
    key: str
    phase: str
    direction: str
    area: str
    text: str
    suggestion: str
    cycles: int
    checkins: int


class PatternsOut(BaseModel):
    status: str  # "learning" until she has check-ins from enough cycles
    cycles_with_checkins: int
    cycles_needed: int
    checkins_used: int
    insights: list[InsightOut]


class SyncArea(BaseModel):
    id: str
    title: str
    personal: list[InsightOut]
    tips: list[Tip]
    myths: list[Myth]


class SyncOut(BaseModel):
    date: date
    phase: str
    phase_title: str
    phase_summary: str
    cycle_day: int
    personal_status: str
    cycles_with_checkins: int
    cycles_needed: int
    areas: list[SyncArea]
    disclaimer: str


class PlanBlock(BaseModel):
    phase: str
    title: str
    start: date
    end: date
    days: int
    is_prediction: bool
    personal: list[InsightOut]


class PlanOut(BaseModel):
    start: date
    blocks: list[PlanBlock]
    personal_status: str
    disclaimer: str
