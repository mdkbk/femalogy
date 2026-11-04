"""Loads the cited knowledge base. Content lives in JSON so it can be edited
and reviewed without touching code."""

import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache
def knowledge() -> dict:
    return json.loads((_DIR / "phases.json").read_text(encoding="utf-8"))


@lru_cache
def sources() -> dict:
    return json.loads((_DIR / "sources.json").read_text(encoding="utf-8"))


@lru_cache
def myths() -> dict:
    return json.loads((_DIR / "myths.json").read_text(encoding="utf-8"))


@lru_cache
def category_to_area() -> dict[str, str]:
    return {c: area for area, a in knowledge()["_meta"]["areas"].items() for c in a["categories"]}


def validate() -> list[str]:
    """Every tip and myth must cite sources that exist. Returns problems."""
    problems = []
    src = sources()
    valid_grades = set(knowledge()["_meta"]["grades"])
    areas = category_to_area()
    for body in knowledge()["phases"].values():
        for tip in body["tips"]:
            if not tip.get("sources"):
                problems.append(f"{tip['id']}: no sources")
            for s in tip.get("sources", []):
                if s not in src:
                    problems.append(f"{tip['id']}: unknown source {s}")
            if tip.get("grade") not in valid_grades:
                problems.append(f"{tip['id']}: bad grade {tip.get('grade')}")
            if tip.get("category") not in areas:
                problems.append(f"{tip['id']}: category {tip.get('category')} has no sync area")
    m = myths()
    verdicts = set(m["_meta"]["verdicts"])
    phases = set(knowledge()["phases"])
    for myth in m["myths"]:
        if not myth.get("sources"):
            problems.append(f"{myth['id']}: no sources")
        for s in myth.get("sources", []):
            if s not in src:
                problems.append(f"{myth['id']}: unknown source {s}")
        if myth.get("verdict") not in verdicts:
            problems.append(f"{myth['id']}: bad verdict {myth.get('verdict')}")
        if myth.get("area") not in knowledge()["_meta"]["areas"]:
            problems.append(f"{myth['id']}: bad area {myth.get('area')}")
        if not set(myth.get("phases", [])) <= phases:
            problems.append(f"{myth['id']}: unknown phase in {myth.get('phases')}")
    return problems
