import os
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
        self.ticker = None
        self.registry = InstrumentRegistry()

    def start(self):
        if not self.api_key or not self.access_token:
            print("[KITE] Skipping start — missing credentials")
            return

        load_info = self.registry.load_from_file(self.instrument_file)
        print(f"[KITE] Instrument load: {load_info}")

        tokens = self._build_subscription_tokens()
        if not tokens:
            print("[KITE] No tokens to subscribe — check instruments file")
            return

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
            print(f"[KITE] Connected, subscribing {len(tokens)} tokens")
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)

        def on_close(ws, code, reason):
            print(f"[KITE] Closed: {code} {reason}")

        self.ticker.on_ticks = on_ticks
        self.ticker.on_connect = on_connect
        self.ticker.on_close = on_close

        self.ticker.connect(threaded=True)

    def _build_subscription_tokens(self):
        tokens = []

        # underlying spot token (if available)
        for inst in self.registry.by_token.values():
            if inst.tradingsymbol == self.underlying and inst.instrument_type == "EQ":
                tokens.append(inst.instrument_token)

        # option chain tokens (limited window)
        option_tokens = self.registry.option_tokens(self.underlying, limit=20)
        tokens.extend(option_tokens)

        return list(set(tokens))
