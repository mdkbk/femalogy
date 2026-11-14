# Femalogy: one container serves the web app and the API from the same address.

# ---- 1. build the web app ----
FROM node:22-slim AS web
WORKDIR /web
COPY femalogy-web/package.json femalogy-web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY femalogy-web/ ./
RUN npm run build

# ---- 2. the API, serving the built app ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    ENV=production WEB_DIST=/app/web PATH="/app/.venv/bin:$PATH"
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
# exact package versions from uv.lock
COPY femalogy-backend/pyproject.toml femalogy-backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY femalogy-backend/ ./
RUN uv sync --frozen --no-dev
COPY --from=web /web/dist /app/web
# never run as root
RUN useradd --system --uid 10001 femalogy && chown -R femalogy /app
USER femalogy
EXPOSE 8000
# apply database migrations, then start; trust the host's proxy for the real client IP and https
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
