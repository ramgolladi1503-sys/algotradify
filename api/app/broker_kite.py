import os
from kiteconnect import KiteTicker
from .market_data import MarketTick

class KiteAdapter:
    def __init__(self, service):
        self.service = service
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.ticker = None

    def start(self):
        if not self.api_key or not self.access_token:
            print("[KITE] Skipping start — missing credentials")
            return

        self.ticker = KiteTicker(self.api_key, self.access_token)

        def on_ticks(ws, ticks):
            for t in ticks:
                tick = MarketTick(
                    symbol=str(t.get("tradingsymbol", "UNKNOWN")),
                    ltp=t.get("last_price"),
                    bid=(t.get("depth", {}).get("buy", [{}])[0].get("price") if t.get("depth") else None),
                    ask=(t.get("depth", {}).get("sell", [{}])[0].get("price") if t.get("depth") else None),
                    volume=t.get("volume"),
                    source="kite_ws"
                )
                self.service.ingest_market(tick)

        def on_connect(ws, response):
            print("[KITE] Connected")
            ws.subscribe([256265])  # NIFTY index token (example)
            ws.set_mode(ws.MODE_FULL, [256265])

        def on_close(ws, code, reason):
            print(f"[KITE] Closed: {code} {reason}")

        self.ticker.on_ticks = on_ticks
        self.ticker.on_connect = on_connect
        self.ticker.on_close = on_close

        self.ticker.connect(threaded=True)
