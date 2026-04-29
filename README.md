# Algotradify Runtime Bridge

This repository connects `core_bot` runtime artifacts/events to a local API and UI.

## Current architecture
- `core_bot/`: trading engine and runtime artifacts (`core_bot/.runtime/...`)
- `api/server.py`: FastAPI runtime bridge + websocket stream
- `runner/live_wrapper.py`: wrapper entrypoint that loads `core_bot.main`
- `frontend/`: Vite React UI for runtime health, snapshot, opportunities, and live events

## What is integrated
- Wrapper boot path surfaces real import failures (`runner/live_wrapper.py`).
- Backend reads runtime artifacts and exposes:
  - `GET /health`
  - `GET /runtime/health`
  - `GET /runtime/snapshot`
  - `GET /opportunities?limit=...`
- Backend websocket (`/ws`):
  - forwards Redis `tradebot_events`
  - emits `runtime_snapshot` updates
  - degrades cleanly if Redis is unavailable
- Frontend renders runtime health, cycle snapshot, opportunities, and live event feed.

## Prerequisites
- Python 3.11+
- Node.js 18+
- Redis on `localhost:6379`

## Setup
1. Create and activate a Python virtual environment.
2. Install API dependencies:
   - `pip install -r api/requirements.txt`
3. Install core bot dependencies:
   - `pip install -r core_bot/requirements.txt`
4. Install frontend dependencies:
   - `npm --prefix frontend install`

## Run
Use separate terminals.

1. Redis:
```bash
redis-server
```

2. Backend:
```bash
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

3. Frontend:
```bash
npm --prefix frontend run dev -- --host 0.0.0.0 --port 3000
```

Optional wrapper process:
```bash
python -m runner.live_wrapper
```

## Local checks
- Backend health: `http://localhost:8000/health`
- Runtime health: `http://localhost:8000/runtime/health`
- Runtime snapshot: `http://localhost:8000/runtime/snapshot`
- Opportunities: `http://localhost:8000/opportunities?limit=20`
- Frontend: `http://localhost:3000`

## Environment knobs
- `CORE_BOT_RUNTIME_ROOT`: override runtime artifact root (default: `core_bot/.runtime`)
- Frontend config (see `frontend/.env.example`):
  - `VITE_API_BASE_URL`
  - `VITE_WS_URL`
  - `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_WS_URL` (fallback support)

## Extended endpoint compatibility (from integrated UI variants)
Some alternate UI builds in this repo history also attempt these endpoints if present:
- `/runtime/risk`
- `/runtime/execution`
- `/opportunities/:id`
- `/trades/:id`
- `/incidents`
- `/verification-checks`
- `/analytics/pnl-curve`
- `/analytics/candidate-volume`
- `/analytics/blocker-frequency`
- `/analytics/strategy-hit-rate`
