import os
import threading
import time
from kiteconnect import KiteTicker
from .market_data import MarketTick
from .instruments import InstrumentRegistry


class KiteAdapter:
    def __init__(self, service):
        self.service = service
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.instrument_file = os.getenv("KITE_INSTRUMENTS_FILE", "instruments.json")
        self.underlying = os.getenv("KITE_UNDERLYING", "NIFTY")
        self.refresh_interval = int(os.getenv("KITE_REFRESH_SEC", "60"))
        self.ticker = None
        self.registry = InstrumentRegistry()
        self._current_tokens = []

    def start(self):
        if not self.api_key or not self.access_token:
            print("[KITE] Skipping start — missing credentials")
            return

        load_info = self.registry.load_from_file(self.instrument_file)
        print(f"[KITE] Instrument load: {load_info}")

        self.ticker = KiteTicker(self.api_key, self.access_token)

        def on_ticks(ws, ticks):
            for t in ticks:
                token = t.get("instrument_token")
                inst = self.registry.get_by_token(token)
                symbol = inst.tradingsymbol if inst else str(token)

                depth = t.get("depth") or {}
                bid = (depth.get("buy") or [{}])[0].get("price") if depth else None
                ask = (depth.get("sell") or [{}])[0].get("price") if depth else None

                tick = MarketTick(
                    symbol=symbol,
                    ltp=t.get("last_price"),
                    bid=bid,
                    ask=ask,
                    volume=t.get("volume"),
                    source="kite_ws",
                )
                self.service.ingest_market(tick)

        def on_connect(ws, response):
            print("[KITE] Connected")
            self._refresh_subscription(ws)

        def on_close(ws, code, reason):
            print(f"[KITE] Closed: {code} {reason}")

        self.ticker.on_ticks = on_ticks
        self.ticker.on_connect = on_connect
        self.ticker.on_close = on_close

        self.ticker.connect(threaded=True)

        # background refresh loop
        threading.Thread(target=self._refresh_loop, daemon=True).start()

    def _refresh_loop(self):
        while True:
            try:
                time.sleep(self.refresh_interval)
                if self.ticker and self.ticker.is_connected():
                    self._refresh_subscription(self.ticker)
            except Exception as e:
                print(f"[KITE] refresh error: {e}")

    def _refresh_subscription(self, ws):
        spot = self._get_spot()
        tokens = self.registry.option_tokens(self.underlying, spot=spot, strikes_each_side=10)

        if set(tokens) != set(self._current_tokens):
            print(f"[KITE] updating subscription → {len(tokens)} tokens (spot={spot})")
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)
            self._current_tokens = tokens

    def _get_spot(self):
        # try to get spot from service snapshots
        snaps = self.service.get_market()
        for s in snaps:
            if s.symbol == self.underlying and s.ltp:
                return s.ltp
        return None
