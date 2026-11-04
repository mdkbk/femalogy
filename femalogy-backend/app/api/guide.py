from fastapi import APIRouter, HTTPException

from app.cycle.engine import Phase
from app.knowledge.loader import knowledge, sources
from app.schemas import PhaseGuide, Source, Tip

router = APIRouter(tags=["guide"])


def _source(sid: str) -> Source:
    s = sources()[sid]
    return Source(
        id=sid, authors=s["authors"], year=s["year"], title=s["title"],
        journal=s["journal"], doi=s["doi"], url=f"https://doi.org/{s['doi']}",
    )


def build_guide(phase: str) -> PhaseGuide:
    body = knowledge()["phases"][phase]
    tips = [
        Tip(id=t["id"], category=t["category"], text=t["text"], grade=t["grade"],
            sources=[_source(s) for s in t["sources"]])
        for t in body["tips"]
    ]
    return PhaseGuide(phase=phase, title=body["title"], summary=body["summary"], tips=tips)


@router.get("/guide/{phase}", response_model=PhaseGuide)
def guide(phase: Phase):
    return build_guide(phase.value)


@router.get("/sources", response_model=list[Source])
def all_sources():
    return [_source(sid) for sid in sources()]


@router.get("/sources/{source_id}", response_model=Source)
def one_source(source_id: str):
    if source_id not in sources():
        raise HTTPException(404, "Unknown source")
    return _source(source_id)
