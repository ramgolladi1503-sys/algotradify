
Algotradify Runtime Bridge

This repo wires the `core_bot` engine to a local API + websocket + UI.

## What works
- Wrapper boot path: `runner/live_wrapper.py` loads `core_bot.main` and exposes real import errors.
- Backend runtime bridge: `api/server.py` serves runtime snapshots and opportunities from `core_bot/.runtime`.
- Event stream: backend websocket forwards Redis `tradebot_events` and emits `runtime_snapshot`.
- Frontend: `frontend/main.jsx` renders runtime health, cycle snapshot, opportunities, and live events.

## Prerequisites
- Python 3.11+ (or a compatible version for your `core_bot` deps)
- Node.js 18+
- Redis server on `localhost:6379`

## Setup
1. Create and activate a Python virtual environment.
2. Install API deps:
   - `pip install -r api/requirements.txt`
3. Install core bot deps:
   - `pip install -r core_bot/requirements.txt`
4. Install frontend deps:
   - `npm --prefix frontend install`

## Run (3 terminals)
1. Redis:
   - `redis-server`
2. Backend API:
   - `python -m uvicorn api.server:app --host 0.0.0.0 --port 8000`
3. Frontend:
   - `npm --prefix frontend run dev -- --host 0.0.0.0 --port 3000`

Optional wrapper terminal:
- `python -m runner.live_wrapper`

## Local checks
- Backend health: `http://localhost:8000/health`
- Runtime health: `http://localhost:8000/runtime/health`
- Runtime snapshot: `http://localhost:8000/runtime/snapshot`
- Opportunities: `http://localhost:8000/opportunities?limit=20`
- Frontend: `http://localhost:3000`

## Env knobs
- `CORE_BOT_RUNTIME_ROOT`: override runtime artifact root (defaults to `core_bot/.runtime`)
- Frontend:
  - `VITE_API_BASE_URL`
  - `VITE_WS_URL`
  - `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_WS_URL` (fallback support)
