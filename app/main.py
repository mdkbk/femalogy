from fastapi import FastAPI

from app.api import auth, cycle, guide
from app.config import get_settings
from app.knowledge.loader import validate

problems = validate()
if problems:  # refuse to start with uncited or broken content
    raise RuntimeError("Knowledge base problems: " + "; ".join(problems))

app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
    description="Cycle tracking + evidence-backed phase guide. All phase dates are estimates.",
)
app.include_router(auth.router)
app.include_router(cycle.router)
app.include_router(guide.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
