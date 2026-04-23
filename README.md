# Integrated Tradebot UI

This package is a cleaned and partially integrated version of the uploaded UI.

## What changed
- Removed the fake/mock data layer from active use.
- Added REST API adapters with endpoint fallbacks.
- Added WebSocket live event ingestion via Zustand.
- Wired React Query snapshot fetching with live event overlays.
- Added environment-based API/WS configuration.
- Removed bundled junk from the final zip: `node_modules`, `.next`, `.DS_Store`, `__MACOSX`.

## Environment
Copy `.env.example` to `.env.local` and adjust if needed.

## Expected backend endpoints
The UI tries these routes, in order, and falls back safely when one is missing:
- `/runtime/health`
- `/runtime/risk`
- `/runtime/execution`
- `/opportunities`
- `/opportunities/:id`
- `/trades/:id`
- `/incidents`
- `/verification-checks`
- `/analytics/pnl-curve`
- `/analytics/candidate-volume`
- `/analytics/blocker-frequency`
- `/analytics/strategy-hit-rate`
- WebSocket: `/ws`

## Run
```bash
npm install
cp .env.example .env.local
npm run dev
```

## Verification
- `npx tsc --noEmit` passed in the packaging environment.
- `next build` could not be fully verified in the packaging environment because Next attempted to fetch SWC using a restricted npm registry command in the container.
