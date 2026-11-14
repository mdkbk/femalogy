from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.api import auth, cycle, guide, sync
from app.config import get_settings, startup_problems
from app.knowledge.loader import validate

problems = validate()
if problems:  # refuse to start with uncited or broken content
    raise RuntimeError("Knowledge base problems: " + "; ".join(problems))

settings = get_settings()
problems = startup_problems(settings)
if problems:  # refuse to start with weak or missing secrets
    raise RuntimeError("Config problems: " + "; ".join(problems))

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Cycle tracking + evidence-backed phase guide. All phase dates are estimates.",
    # interactive API docs only while developing
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(cycle.router)
api.include_router(guide.router)
api.include_router(sync.router)


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(api)


# ---------------------------------------------------------------- security middleware

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
# Content Security Policy: only our own code, styles and fonts load (nothing third-party); no framing.
# 'unsafe-inline' styles are needed for React style attributes; scripts stay strictly 'self'.
CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def _origin_ok(request: Request) -> bool:
    """Blocks cross-site request forgery: a state-changing request must come from our own pages.
    The mobile app authenticates with a Bearer header (not a cookie), so it isn't affected."""
    if request.headers.get("authorization", "").lower().startswith("bearer "):
        return True
    origin = request.headers.get("origin")
    if origin:
        allowed = {request.headers.get("host", "")}
        if not settings.is_production:
            allowed |= {urlsplit(o).netloc for o in settings.cors_origin_list}
        return urlsplit(origin).netloc in allowed
    if settings.session_cookie in request.cookies:
        # a browser sending our cookie without an Origin: only trust same-origin fetches
        return request.headers.get("sec-fetch-site") == "same-origin"
    return True  # no cookie and no Origin: not a browser riding on a session


@app.middleware("http")
async def security(request: Request, call_next):
    path = request.url.path
    if request.method in UNSAFE and path.startswith("/api/") and not _origin_ok(request):
        return JSONResponse({"detail": "Request blocked: it didn't come from Femalogy."}, status_code=403)
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("Referrer-Policy", "same-origin")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    if not path.startswith("/api/docs"):
        h.setdefault("Content-Security-Policy", CSP)
    if settings.is_production:
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if path.startswith("/api/"):
        h["Cache-Control"] = "no-store"  # health data must not sit in browser or proxy caches
    return response


# ---------------------------------------------------------------- the web app (same origin as the API)

dist = Path(settings.web_dist).resolve() if settings.web_dist else None
if dist and (dist / "index.html").is_file():

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (dist / path).resolve()
        if path and file.is_file() and dist in file.parents:  # stays inside dist: no path tricks
            cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
            return FileResponse(file, headers={"Cache-Control": cache})
        # every app route (/, /plan, /guide, ...) loads the single-page app
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
