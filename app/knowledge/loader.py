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


def validate() -> list[str]:
    """Every tip must cite at least one source that exists. Returns problems."""
    problems = []
    src = sources()
    valid_grades = set(knowledge()["_meta"]["grades"])
    for body in knowledge()["phases"].values():
        for tip in body["tips"]:
            if not tip.get("sources"):
                problems.append(f"{tip['id']}: no sources")
            for s in tip.get("sources", []):
                if s not in src:
                    problems.append(f"{tip['id']}: unknown source {s}")
            if tip.get("grade") not in valid_grades:
                problems.append(f"{tip['id']}: bad grade {tip.get('grade')}")
    return problems
