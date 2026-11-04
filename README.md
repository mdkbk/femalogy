# Femalogy

Evidence-based cycle syncing. Femalogy tracks the cycle, shows which phase she's in, and gives phase guidance where every tip carries an evidence grade and its peer-reviewed sources. Over time it learns her own pattern from check-ins.

| Folder | What |
| --- | --- |
| [`femalogy-backend/`](femalogy-backend) | Python API: FastAPI, PostgreSQL, cycle prediction engine, personal pattern engine, cited knowledge base |
| [`femalogy-web/`](femalogy-web) | Web app: React + Vite + TypeScript |

## Run it locally

Nothing is installed system-wide. Each part keeps its own tools inside its folder.

```bash
cd femalogy-backend && ./setup.sh   # first time
./run.sh                            # API on http://localhost:8000 (docs at /docs)
```

```bash
cd femalogy-web && ./setup.sh       # first time
./run.sh                            # app on http://localhost:5173
```

The backend needs a `.env`: copy `femalogy-backend/.env.example` and fill in the two secrets (see the backend README).

## How predictions work

Fitted and backtested on real cycle data. See [femalogy-backend/docs/prediction-model.md](femalogy-backend/docs/prediction-model.md).

General information, not medical advice. Dates are estimates and must not be used for contraception.
