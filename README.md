# Femalogy backend

Python API for Femalogy: cycle tracking + a phase guide where every tip has a peer-reviewed source and an evidence grade.

Stack: FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · Argon2 + JWT · Fernet field encryption.

## Run it

With Docker (easiest):

```bash
cp .env.example .env        # then fill JWT_SECRET and FIELD_ENCRYPTION_KEY
docker compose up --build
```

API on http://localhost:8000, interactive docs on http://localhost:8000/docs.

Without Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # point DATABASE_URL at your Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Generate the two secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"                                  # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"     # FIELD_ENCRYPTION_KEY
```

Keep FIELD_ENCRYPTION_KEY safe. If it's lost, encrypted check-in notes can't be read again.

## Tests

```bash
pytest -q                                   # SQLite, fast
TEST_DATABASE_URL=postgresql+psycopg://user@localhost/femalogy_test pytest -q   # real Postgres
ruff check .
```

## Layout

```
app/
  cycle/engine.py        cycle day, phase, ovulation + next period estimates (pure functions)
  knowledge/phases.json  phase guide content: tips, grades, red flags
  knowledge/sources.json the papers every tip cites (DOI + PMID + key finding)
  knowledge/loader.py    loads content; app refuses to start if a tip is uncited
  api/                   auth, periods, today, calendar, check-ins, guide, sources
  models.py              users, periods, check-ins (notes encrypted)
alembic/                 migrations
tests/                   engine, knowledge base and API tests
```

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | /auth/register | Create account, returns token |
| POST | /auth/login | Form login (username = email), returns token |
| GET/PUT/DELETE | /me | Profile; DELETE wipes the account and all data |
| POST/GET | /periods | Log a period start (and end), list them |
| PATCH/DELETE | /periods/{id} | Fix or remove a logged period |
| GET | /today?on=YYYY-MM-DD | Cycle day, phase, estimates, flags, phase guide |
| GET | /calendar?days=35 | Predicted phase per day |
| PUT/GET | /checkins | Daily mood, energy, sleep, symptoms, notes (one per day) |
| GET | /guide/{phase} | Tips for a phase with sources |
| GET | /sources | Every paper the app cites |

## How the engine estimates things

Full write-up with the backtest: [docs/prediction-model.md](docs/prediction-model.md).

- Cycle length = empirical-Bayes blend of her last 6 cycles and the population average (29.3 days). The more she logs, the more it trusts her own data. Fitted and validated on real cycles (Marquette study, 159 women, held out by woman): 2.24 days average error vs 2.32 for a plain median.
- A cycle about twice her usual length counts as a period that wasn't logged (`possible_missed_period` flag + date to ask her about), so one missed log can't push predictions weeks out.
- Next period comes with an 80% range (`next_period_earliest` / `next_period_latest`), calibrated on held-out data.
- Ovulation day = next period − 13 days (best fit to measured ovulation), shown as a 3-day window.
- Confidence drops to low if her recent cycles differ by more than 9 days.
- Flags: `period_late`, `no_period_90_days`, `high_variability`, `needs_more_data`, `possible_missed_period`.
- Everything is an estimate. The API marks it as one and the app must never present it as contraception.

## Before launch

- Content in `app/knowledge/phases.json` is a draft. A gynecologist and a nutritionist should review it.
- The red-flag texts (heavy bleeding, severe pain) are standard safety advice but aren't cited yet. Add a clinical source during review.
- `/today` uses the server's date if `on` isn't passed. The mobile app should always send the user's local date.
