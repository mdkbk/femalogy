from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cycle, guide
from app.config import get_settings
from app.knowledge.loader import validate

problems = validate()
if problems:  # refuse to start with uncited or broken content
    raise RuntimeError("Knowledge base problems: " + "; ".join(problems))

settings = get_settings()
if len(settings.jwt_secret) < 32 or settings.jwt_secret in ("change-me", "replace-me"):
    raise RuntimeError("JWT_SECRET is missing or too short. Set a long random value in .env")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Cycle tracking + evidence-backed phase guide. All phase dates are estimates.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(cycle.router)
app.include_router(guide.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
