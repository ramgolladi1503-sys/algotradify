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
        raw_underlyings = os.getenv("KITE_UNDERLYINGS") or os.getenv("KITE_UNDERLYING", "NIFTY")
        self.underlyings = [u.strip().upper() for u in raw_underlyings.split(",") if u.strip()]
        self.strikes_each_side = int(os.getenv("KITE_STRIKES_EACH_SIDE", "10"))
        self.refresh_interval = int(os.getenv("KITE_REFRESH_SEC", "60"))
        self.ticker = None
        self.registry = InstrumentRegistry()
        self._current_tokens = []
        self._last_chain_state = {}

    def start(self):
        if not self.api_key or not self.access_token:
            print("[KITE] Skipping start — missing credentials")
            return

        load_info = self.registry.load_from_file(self.instrument_file)
        print(f"[KITE] Instrument load: {load_info}")
        print(f"[KITE] Underlyings: {self.underlyings}")

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
        tokens = []
        chain_state = {}

        for underlying in self.underlyings:
            spot = self._get_spot(underlying)
            chain = self.registry.option_chain(
                underlying,
                spot=spot,
                strikes_each_side=self.strikes_each_side,
            )
            chain_tokens = self.registry.option_tokens(
                underlying,
                spot=spot,
                strikes_each_side=self.strikes_each_side,
            )
            tokens.extend(chain_tokens)
            chain_state[underlying] = {
                "spot": spot,
                "atm": chain.atm,
                "expiry": chain.expiry,
                "token_count": chain.token_count,
                "strike_count": len(chain.rows),
            }

        unique_tokens = sorted(set(tokens))
        self._last_chain_state = chain_state

        if set(unique_tokens) != set(self._current_tokens):
            print(f"[KITE] updating subscription → {len(unique_tokens)} tokens | chains={chain_state}")
            if self._current_tokens:
                try:
                    ws.unsubscribe(self._current_tokens)
                except Exception as e:
                    print(f"[KITE] unsubscribe warning: {e}")
            if unique_tokens:
                ws.subscribe(unique_tokens)
                ws.set_mode(ws.MODE_FULL, unique_tokens)
            self._current_tokens = unique_tokens

    def _get_spot(self, underlying):
        snaps = self.service.get_market()
        for s in snaps:
            if s.symbol == underlying and s.ltp:
                return s.ltp
        return None

    def chain_state(self):
        return {
            "underlyings": self.underlyings,
            "strikes_each_side": self.strikes_each_side,
            "current_token_count": len(self._current_tokens),
            "chains": self._last_chain_state,
            "instrument_stats": self.registry.stats(),
        }
