
FINAL TRADEBOT FULLSTACK

Run:

1. redis-server
2. uvicorn api.server:app --reload
3. python runner/live_wrapper.py
4. cd frontend && npm install && npm run dev

NOTE:
- Place your bot inside core_bot/
- Integration is event-driven (no file observer)
