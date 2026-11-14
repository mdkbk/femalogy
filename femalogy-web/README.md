# Femalogy web app

React + Vite + TypeScript front end for the Femalogy API: evidence-based cycle syncing.

## Run it

Everything (Node, packages) stays inside this folder. Nothing is installed on your computer.

```bash
./setup.sh      # one time: portable Node into .tools/, packages into node_modules/
./run.sh        # opens http://localhost:5173
```

The backend has to be running too (`../femalogy-backend/run.sh`). In dev, the app calls `/api/...` and Vite forwards that to `http://localhost:8000`, so there are no CORS issues. Point it somewhere else with `FEMALOGY_API=http://host:port ./run.sh`.

Type check and production build:

```bash
PATH="$PWD/.tools/node/bin:$PATH" npm run build     # output in dist/
```

In production the backend serves this app's built files itself (see the root `Dockerfile`), so the app and `/api` share one address and the session cookie just works. Nothing to configure.

## Screens

| Route | What it shows |
| --- | --- |
| `/` Today | Cycle ring, phase, estimates, and the sync plan per area: her own patterns, research tips, myth checks |
| `/plan` Plan | Month calendar by phase, the next 8 weeks as phase blocks with her patterns, log and edit periods |
| `/check-in` | Mood, energy, sleep, symptoms, encrypted notes. Red flags show right away |
| `/guide` | All four phases with filters, plus every myth check |

New users get asked for their last period start before anything else.

## Layout

```
src/
  api.ts            typed client, mirrors the backend schemas; always sends the user's local date
  auth.tsx          sign in / sign up / sign out, token in localStorage
  lib.ts            phase colours, grades, date helpers, useLoad hook
  styles.css        design tokens + all styles (soft and warm theme, motion respects reduced-motion)
  components/ui.tsx layout, cycle ring, tip / insight / myth cards
  pages/            Today, Plan, Checkin, Guide, Welcome
```
