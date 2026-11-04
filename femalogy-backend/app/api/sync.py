"""Cycle syncing: research tips + her own patterns + myth checks, per area."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.cycle import _status_for
from app.api.deps import current_user
from app.api.guide import _source, build_guide
from app.cycle.engine import phase_calendar
from app.cycle.patterns import CheckinPoint, Insight, PatternReport, find_patterns
from app.knowledge.loader import category_to_area, knowledge, myths
from app.models import User
from app.schemas import InsightOut, Myth, PatternsOut, PlanBlock, PlanOut, SyncArea, SyncOut

router = APIRouter(tags=["sync"])

PHASE_NAME = {"menstrual": "period", "follicular": "follicular phase",
              "ovulation": "ovulation days", "luteal": "luteal phase"}
METRIC = {"mood": ("mood", "mood"), "energy": ("energy", "movement"), "sleep_quality": ("sleep", "sleep")}
SYMPTOM = {
    "cramps": "cramps", "headache": "headaches", "bloating": "bloating",
    "breast_tenderness": "breast tenderness", "acne": "acne", "back_pain": "back pain",
    "fatigue": "tiredness", "cravings": "cravings", "nausea": "nausea",
    "very_heavy_bleeding": "very heavy bleeding", "severe_pain": "severe pain",
}
SYMPTOM_AREA = {"cravings": "food", "fatigue": "mood"}
SUGGEST = {
    ("energy", "lower"): "Plan lighter training and easier days here, if that suits you.",
    ("energy", "higher"): "A good window for your hardest workouts or busiest days.",
    ("mood", "lower"): "Keep some downtime here and try not to stack stressful plans.",
    ("mood", "higher"): "You tend to feel good here, a nice time for social plans or big conversations.",
    ("sleep_quality", "lower"): "Plan earlier, lighter evenings on these days.",
    ("sleep_quality", "higher"): "Your sleep is usually good here.",
}


def _insight_out(i: Insight) -> InsightOut:
    where = PHASE_NAME[i.phase.value]
    if i.kind == "metric":
        label, area = METRIC[i.key]
        text = (f"Your {label} is usually {i.direction} in your {where}: "
                f"{i.phase_value} vs {i.baseline} in the rest of your cycle, seen in {i.cycles} cycles.")
        suggestion = SUGGEST[(i.key, i.direction)]
    else:
        area = SYMPTOM_AREA.get(i.key, "body")
        text = (f"You often log {SYMPTOM.get(i.key, i.key)} in your {where}: "
                f"{round(i.phase_value * 100)}% of those check-ins, across {i.cycles} cycles.")
        suggestion = "Your sync plan has research tips for this phase that may help."
    return InsightOut(id=i.id, kind=i.kind, key=i.key, phase=i.phase.value, direction=i.direction,
                      area=area, text=text, suggestion=suggestion, cycles=i.cycles, checkins=i.checkins)


def _myth_out(m: dict) -> Myth:
    labels = myths()["_meta"]["verdicts"]
    names = {"not_supported": "Not supported", "partly_true": "Partly true", "false": "False"}
    return Myth(id=m["id"], claim=m["claim"], verdict=m["verdict"],
                verdict_label=f"{names[m['verdict']]}: {labels[m['verdict']]}",
                text=m["text"], area=m["area"], phases=m["phases"],
                sources=[_source(s) for s in m["sources"]])


def _report(user: User, day: date) -> tuple[PatternReport, object]:
    st = _status_for(user, day)
    if not st:
        raise HTTPException(409, "Log your last period start date first")
    points = [
        CheckinPoint(c.day, c.mood, c.energy, c.sleep_quality, list(c.symptoms or []))
        for c in user.checkins if c.day <= day
    ]
    starts = [p.start_date for p in user.periods if p.start_date <= day]
    report = find_patterns(starts, st.cycle_length_estimate, st.period_length_estimate, points)
    return report, st


@router.get("/insights", response_model=PatternsOut)
def insights(on: date | None = Query(default=None), user: User = Depends(current_user)):
    """Her own phase patterns. Status stays 'learning' until there's enough data."""
    report, _ = _report(user, on or date.today())
    return PatternsOut(status=report.status, cycles_with_checkins=report.cycles_with_checkins,
                       cycles_needed=report.cycles_needed, checkins_used=report.checkins_used,
                       insights=[_insight_out(i) for i in report.insights])


@router.get("/sync", response_model=SyncOut)
def sync(on: date | None = Query(default=None, description="The user's local date"),
         user: User = Depends(current_user)):
    """Today's sync plan: per area, her own patterns first, then research tips, then myth checks."""
    day = on or date.today()
    report, st = _report(user, day)
    phase = st.phase.value
    guide = build_guide(phase)
    tips_raw = {t["id"]: t for t in knowledge()["phases"][phase]["tips"]}
    c2a = category_to_area()
    mine = [_insight_out(i) for i in report.insights if i.phase.value == phase]
    areas = []
    for area_id, a in knowledge()["_meta"]["areas"].items():
        areas.append(SyncArea(
            id=area_id, title=a["title"],
            personal=[i for i in mine if i.area == area_id],
            tips=[t for t in guide.tips if c2a[tips_raw[t.id]["category"]] == area_id],
            myths=[_myth_out(m) for m in myths()["myths"] if m["area"] == area_id and phase in m["phases"]],
        ))
    return SyncOut(date=day, phase=phase, phase_title=guide.title, phase_summary=guide.summary,
                   cycle_day=st.cycle_day, personal_status=report.status,
                   cycles_with_checkins=report.cycles_with_checkins, cycles_needed=report.cycles_needed,
                   areas=areas, disclaimer=knowledge()["disclaimer"])


@router.get("/plan", response_model=PlanOut)
def plan(on: date | None = Query(default=None, description="The user's local date"),
         days: int = Query(default=56, ge=7, le=120), user: User = Depends(current_user)):
    """The coming weeks as phase blocks, each with what she usually notices in that phase."""
    day = on or date.today()
    report, st = _report(user, day)
    by_phase: dict[str, list[InsightOut]] = {}
    for i in report.insights:
        by_phase.setdefault(i.phase.value, []).append(_insight_out(i))
    blocks: list[PlanBlock] = []
    for d, p in phase_calendar(st, days):
        if blocks and blocks[-1].phase == p.value and blocks[-1].end == d - timedelta(days=1):
            blocks[-1].end = d
            blocks[-1].days += 1
            continue
        blocks.append(PlanBlock(phase=p.value, title=build_guide(p.value).title, start=d, end=d, days=1,
                                is_prediction=d > day, personal=by_phase.get(p.value, [])))
    return PlanOut(start=day, blocks=blocks, personal_status=report.status,
                   disclaimer=knowledge()["disclaimer"])


@router.get("/myths", response_model=list[Myth])
def all_myths():
    return [_myth_out(m) for m in myths()["myths"]]
