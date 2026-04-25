import csv
import json
import os
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Instrument(BaseModel):
    instrument_token: int
    exchange_token: Optional[int] = None
    tradingsymbol: str
    name: str = ""
    exchange: str = ""
    segment: str = ""
    instrument_type: str = ""
    expiry: Optional[str] = None
    strike: Optional[float] = None
    lot_size: Optional[int] = None
    tick_size: Optional[float] = None


class OptionContract(BaseModel):
    instrument_token: int
    tradingsymbol: str
    underlying: str
    expiry: str
    strike: float
    option_type: str
    lot_size: Optional[int] = None


class OptionChainRow(BaseModel):
    strike: float
    ce: Optional[OptionContract] = None
    pe: Optional[OptionContract] = None


class OptionChain(BaseModel):
    underlying: str
    expiry: str
    rows: List[OptionChainRow]
    token_count: int


class InstrumentRegistry:
    def __init__(self):
        self.by_token: Dict[int, Instrument] = {}
        self.by_symbol: Dict[str, Instrument] = {}
        self.options_by_underlying: Dict[str, List[OptionContract]] = defaultdict(list)

    def load_from_file(self, path: str) -> dict:
        if not os.path.exists(path):
            return {"loaded": 0, "error": f"file_not_found:{path}"}

        if path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        return self.load_rows(rows)

    def load_rows(self, rows: List[dict]) -> dict:
        self.by_token.clear()
        self.by_symbol.clear()
        self.options_by_underlying.clear()

        loaded = 0
        skipped = 0
        for row in rows:
            try:
                inst = self._parse_row(row)
                self.by_token[inst.instrument_token] = inst
                self.by_symbol[inst.tradingsymbol.upper()] = inst
                loaded += 1

                if inst.instrument_type in {"CE", "PE"} and inst.expiry and inst.strike is not None:
                    underlying = self._infer_underlying(inst)
                    self.options_by_underlying[underlying].append(
                        OptionContract(
                            instrument_token=inst.instrument_token,
                            tradingsymbol=inst.tradingsymbol,
                            underlying=underlying,
                            expiry=inst.expiry,
                            strike=inst.strike,
                            option_type=inst.instrument_type,
                            lot_size=inst.lot_size,
                        )
                    )
            except Exception:
                skipped += 1

        for contracts in self.options_by_underlying.values():
            contracts.sort(key=lambda c: (c.expiry, c.strike, c.option_type))

        return {"loaded": loaded, "skipped": skipped, "underlyings": sorted(self.options_by_underlying.keys())}

    def get_by_token(self, token: int) -> Optional[Instrument]:
        return self.by_token.get(int(token))

    def get_by_symbol(self, symbol: str) -> Optional[Instrument]:
        return self.by_symbol.get(symbol.upper())

    def option_chain(self, underlying: str, expiry: Optional[str] = None, limit: Optional[int] = None) -> OptionChain:
        key = underlying.upper().strip()
        contracts = list(self.options_by_underlying.get(key, []))
        if not contracts:
            return OptionChain(underlying=key, expiry=expiry or "", rows=[], token_count=0)

        selected_expiry = expiry or self.nearest_expiry(key)
        contracts = [c for c in contracts if c.expiry == selected_expiry]

        by_strike = defaultdict(dict)
        for c in contracts:
            by_strike[c.strike][c.option_type.lower()] = c

        rows = [OptionChainRow(strike=s, ce=v.get("ce"), pe=v.get("pe")) for s, v in sorted(by_strike.items())]
        if limit and limit > 0:
            mid = len(rows) // 2
            half = limit // 2
            rows = rows[max(0, mid - half): mid + half + 1]

        return OptionChain(underlying=key, expiry=selected_expiry, rows=rows, token_count=sum(1 for r in rows for x in [r.ce, r.pe] if x))

    def option_tokens(self, underlying: str, expiry: Optional[str] = None, limit: Optional[int] = None) -> List[int]:
        chain = self.option_chain(underlying, expiry, limit)
        tokens = []
        for row in chain.rows:
            if row.ce:
                tokens.append(row.ce.instrument_token)
            if row.pe:
                tokens.append(row.pe.instrument_token)
        return tokens

    def nearest_expiry(self, underlying: str) -> str:
        expiries = sorted({c.expiry for c in self.options_by_underlying.get(underlying.upper(), [])})
        today = date.today().isoformat()
        future = [e for e in expiries if e >= today]
        return (future or expiries or [""])[0]

    def stats(self) -> dict:
        return {
            "instrument_count": len(self.by_token),
            "symbol_count": len(self.by_symbol),
            "underlyings": sorted(self.options_by_underlying.keys()),
            "option_count": sum(len(v) for v in self.options_by_underlying.values()),
        }

    def _parse_row(self, row: dict) -> Instrument:
        def as_int(v):
            return int(float(v)) if v not in {None, ""} else None

        def as_float(v):
            return float(v) if v not in {None, ""} else None

        expiry = row.get("expiry") or None
        if isinstance(expiry, datetime):
            expiry = expiry.date().isoformat()

        return Instrument(
            instrument_token=as_int(row.get("instrument_token")),
            exchange_token=as_int(row.get("exchange_token")),
            tradingsymbol=str(row.get("tradingsymbol") or "").upper(),
            name=str(row.get("name") or "").upper(),
            exchange=str(row.get("exchange") or ""),
            segment=str(row.get("segment") or ""),
            instrument_type=str(row.get("instrument_type") or "").upper(),
            expiry=str(expiry) if expiry else None,
            strike=as_float(row.get("strike")),
            lot_size=as_int(row.get("lot_size")),
            tick_size=as_float(row.get("tick_size")),
        )

    def _infer_underlying(self, inst: Instrument) -> str:
        if inst.name:
            return inst.name.upper()
        symbol = inst.tradingsymbol.upper()
        for known in ["BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY", "SENSEX"]:
            if symbol.startswith(known):
                return known
        return symbol.rstrip("CEPE")
