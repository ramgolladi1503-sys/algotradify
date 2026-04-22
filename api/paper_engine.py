from __future__ import annotations

import json
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRADEBOT_ROOT = Path(os.getenv("TRADEBOT_ROOT", "core_bot")).resolve()
RUNTIME_DIR = TRADEBOT_ROOT / ".runtime"
ACTION_QUEUE_PATH = TRADEBOT_ROOT / "runtime" / "ui_action_queue.jsonl"
ACTION_CURSOR_PATH = TRADEBOT_ROOT / "runtime" / "paper_action_cursor.json"
PAPER_POSITIONS_PATH = TRADEBOT_ROOT / "runtime" / "paper_positions.json"
PAPER_TRADES_PATH = TRADEBOT_ROOT / "runtime" / "paper_trades.json"
PAPER_PNL_PATH = TRADEBOT_ROOT / "runtime" / "paper_pnl.json"
PAPER_LEARNING_PATH = TRADEBOT_ROOT / "runtime" / "paper_learning.json"
ADAPTIVE_PARAMS_PATH = TRADEBOT_ROOT / "runtime" / "adaptive_params.json"
PAPER_REJECTIONS_PATH = TRADEBOT_ROOT / "runtime" / "paper_rejections.json"
BANDIT_STATE_PATH = TRADEBOT_ROOT / "runtime" / "bandit_state.json"

DEFAULT_QTY = int(os.getenv("PAPER_DEFAULT_QTY", "1") or "1")
DEFAULT_STOP_PCT = float(os.getenv("PAPER_DEFAULT_STOP_PCT", "0.15") or "0.15")
DEFAULT_TARGET_PCT = float(os.getenv("PAPER_DEFAULT_TARGET_PCT", "0.25") or "0.25")
DEFAULT_SLIPPAGE_PCT = float(os.getenv("PAPER_SLIPPAGE_PCT", "0.002") or "0.002")
DEFAULT_TIME_EXIT_SEC = int(os.getenv("PAPER_TIME_EXIT_SEC", "900") or "900")
BANDIT_EPSILON = float(os.getenv("PAPER_BANDIT_EPSILON", "0.18") or "0.18")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "None"):
            return None
        return float(value)
    except Exception:
        return None


def _unwrap_payload(blob: Any) -> Any:
    if isinstance(blob, dict) and isinstance(blob.get("payload"), (dict, list)):
        return blob["payload"]
    return blob


def _default_params() -> dict[str, float]:
    return {
        "score_threshold": 0.5,
        "confidence_threshold": 0.4,
        "momentum_threshold": 0.4,
        "risk_reward_ratio": 1.5,
        "trade_frequency": 1.0,
    }


def _default_bandit_arms() -> list[dict[str, Any]]:
    return [
        {"arm_id": "balanced", "label": "Balanced", "params": {"score_threshold": 0.50, "confidence_threshold": 0.40, "momentum_threshold": 0.40, "risk_reward_ratio": 1.50, "trade_frequency": 1.00}},
        {"arm_id": "conservative", "label": "Conservative", "params": {"score_threshold": 0.65, "confidence_threshold": 0.55, "momentum_threshold": 0.55, "risk_reward_ratio": 1.80, "trade_frequency": 0.70}},
        {"arm_id": "aggressive", "label": "Aggressive", "params": {"score_threshold": 0.38, "confidence_threshold": 0.30, "momentum_threshold": 0.30, "risk_reward_ratio": 1.20, "trade_frequency": 1.25}},
        {"arm_id": "momentum_focus", "label": "Momentum Focus", "params": {"score_threshold": 0.58, "confidence_threshold": 0.45, "momentum_threshold": 0.65, "risk_reward_ratio": 1.70, "trade_frequency": 0.85}},
        {"arm_id": "high_rr", "label": "High RR", "params": {"score_threshold": 0.55, "confidence_threshold": 0.45, "momentum_threshold": 0.45, "risk_reward_ratio": 2.20, "trade_frequency": 0.75}},
    ]


def _smooth(old: float, new: float, alpha: float = 0.2) -> float:
    return (old * (1.0 - alpha)) + (new * alpha)


def load_adaptive_params() -> dict[str, float]:
    data = _read_json(ADAPTIVE_PARAMS_PATH, default={})
    params = _default_params()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in params and _safe_float(value) is not None:
                params[key] = float(value)
    return params


def save_adaptive_params(params: dict[str, float]) -> None:
    _write_json(ADAPTIVE_PARAMS_PATH, params)


def _default_bandit_state() -> dict[str, Any]:
    arms = []
    for arm in _default_bandit_arms():
        arms.append({
            "arm_id": arm["arm_id"],
            "label": arm["label"],
            "params": arm["params"],
            "pulls": 0,
            "wins": 0,
            "losses": 0,
            "total_reward": 0.0,
            "avg_reward": 0.0,
            "last_reward": None,
        })
    return {
        "generated_at": _utc_now(),
        "epsilon": BANDIT_EPSILON,
        "total_pulls": 0,
        "last_selected_arm": None,
        "last_selection_reason": None,
        "last_updated_trade_id": None,
        "arms": arms,
    }


def load_bandit_state() -> dict[str, Any]:
    data = _read_json(BANDIT_STATE_PATH, default={})
    state = _default_bandit_state()
    if isinstance(data, dict):
        arm_map = {arm["arm_id"]: arm for arm in state["arms"]}
        incoming_arms = data.get("arms") if isinstance(data.get("arms"), list) else []
        for incoming in incoming_arms:
            if not isinstance(incoming, dict):
                continue
            arm_id = str(incoming.get("arm_id") or "")
            if arm_id in arm_map:
                target = arm_map[arm_id]
                for field in ("pulls", "wins", "losses"):
                    target[field] = int(incoming.get(field) or target[field])
                for field in ("total_reward", "avg_reward"):
                    target[field] = float(incoming.get(field) or target[field])
                target["last_reward"] = incoming.get("last_reward")
                if isinstance(incoming.get("params"), dict):
                    for p_key, p_val in incoming["params"].items():
                        if p_key in target["params"] and _safe_float(p_val) is not None:
                            target["params"][p_key] = float(p_val)
        state["epsilon"] = float(data.get("epsilon") or state["epsilon"])
        state["total_pulls"] = int(data.get("total_pulls") or state["total_pulls"])
        state["last_selected_arm"] = data.get("last_selected_arm")
        state["last_selection_reason"] = data.get("last_selection_reason")
        state["last_updated_trade_id"] = data.get("last_updated_trade_id")
    return state


def save_bandit_state(state: dict[str, Any]) -> None:
    state["generated_at"] = _utc_now()
    _write_json(BANDIT_STATE_PATH, state)


def select_bandit_arm() -> dict[str, Any]:
    state = load_bandit_state()
    arms = state["arms"]
    untried = [arm for arm in arms if int(arm.get("pulls") or 0) == 0]
    if untried:
        chosen = random.choice(untried)
        state["last_selected_arm"] = chosen["arm_id"]
        state["last_selection_reason"] = "cold_start"
        save_bandit_state(state)
        return chosen
    if random.random() < float(state.get("epsilon") or BANDIT_EPSILON):
        chosen = random.choice(arms)
        state["last_selected_arm"] = chosen["arm_id"]
        state["last_selection_reason"] = "exploration"
        save_bandit_state(state)
        return chosen
    total_pulls = max(sum(int(arm.get("pulls") or 0) for arm in arms), 1)
    best_score = None
    chosen = arms[0]
    for arm in arms:
        pulls = max(int(arm.get("pulls") or 0), 1)
        avg_reward = float(arm.get("avg_reward") or 0.0)
        ucb = avg_reward + math.sqrt((2.0 * math.log(total_pulls + 1)) / pulls)
        if best_score is None or ucb > best_score:
            best_score = ucb
            chosen = arm
    state["last_selected_arm"] = chosen["arm_id"]
    state["last_selection_reason"] = "ucb"
    save_bandit_state(state)
    return chosen


def get_bandit_summary() -> dict[str, Any]:
    state = load_bandit_state()
    ordered = sorted(state["arms"], key=lambda arm: (float(arm.get("avg_reward") or 0.0), float(arm.get("total_reward") or 0.0)), reverse=True)
    return {
        "generated_at": _utc_now(),
        "epsilon": state.get("epsilon"),
        "total_pulls": state.get("total_pulls"),
        "last_selected_arm": state.get("last_selected_arm"),
        "last_selection_reason": state.get("last_selection_reason"),
        "leader": ordered[0] if ordered else None,
        "arms": ordered,
    }


def update_bandit_rewards() -> dict[str, Any]:
    state = load_bandit_state()
    trades = [t for t in _load_trades() if isinstance(t, dict) and t.get("status") == "CLOSED"]
    updated = 0
    arm_map = {arm["arm_id"]: arm for arm in state["arms"]}
    last_updated_trade_id = state.get("last_updated_trade_id")
    seen_last = last_updated_trade_id is None
    for trade in reversed(trades):
        pid = trade.get("paper_position_id")
        if not seen_last:
            if pid == last_updated_trade_id:
                seen_last = True
            continue
        arm_id = trade.get("bandit_arm_id")
        if not arm_id or arm_id not in arm_map:
            continue
        reward = float(trade.get("realized_pnl") or 0.0)
        arm = arm_map[arm_id]
        arm["pulls"] = int(arm.get("pulls") or 0) + 1
        state["total_pulls"] = int(state.get("total_pulls") or 0) + 1
        arm["total_reward"] = round(float(arm.get("total_reward") or 0.0) + reward, 4)
        arm["avg_reward"] = round(float(arm["total_reward"]) / max(int(arm["pulls"]), 1), 4)
        arm["last_reward"] = reward
        if reward > 0:
            arm["wins"] = int(arm.get("wins") or 0) + 1
        elif reward < 0:
            arm["losses"] = int(arm.get("losses") or 0) + 1
        state["last_updated_trade_id"] = pid
        updated += 1
    save_bandit_state(state)
    return {"updated_trades": updated, "bandit": get_bandit_summary()}


def _record_rejection(item: dict[str, Any]) -> None:
    rows = _read_json(PAPER_REJECTIONS_PATH, default=[])
    history = rows if isinstance(rows, list) else []
    history.insert(0, item)
    _write_json(PAPER_REJECTIONS_PATH, history[:200])


def get_rejections() -> list[dict[str, Any]]:
    rows = _read_json(PAPER_REJECTIONS_PATH, default=[])
    return rows if isinstance(rows, list) else []


def _load_action_cursor() -> dict[str, Any]:
    data = _read_json(ACTION_CURSOR_PATH, default={})
    return data if isinstance(data, dict) else {}


def _save_action_cursor(cursor: dict[str, Any]) -> None:
    _write_json(ACTION_CURSOR_PATH, cursor)


def _load_positions() -> list[dict[str, Any]]:
    data = _read_json(PAPER_POSITIONS_PATH, default=[])
    return data if isinstance(data, list) else []


def _save_positions(positions: list[dict[str, Any]]) -> None:
    _write_json(PAPER_POSITIONS_PATH, positions)


def _load_trades() -> list[dict[str, Any]]:
    data = _read_json(PAPER_TRADES_PATH, default=[])
    return data if isinstance(data, list) else []


def _save_trades(trades: list[dict[str, Any]]) -> None:
    _write_json(PAPER_TRADES_PATH, trades)


def _load_opportunities() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    advisory_path = RUNTIME_DIR / "advisory_latest.json"
    top_path = RUNTIME_DIR / "top_opportunities_latest.json"
    advisory = _unwrap_payload(_read_json(advisory_path, default={}))
    top = _unwrap_payload(_read_json(top_path, default={}))
    if isinstance(advisory, dict):
        for row in advisory.get("rows", []):
            if isinstance(row, dict):
                rows.append(row)
    if isinstance(top, dict):
        for key in ("top_executable_opportunities", "top_advisory_opportunities", "rows", "items"):
            for row in top.get(key, []) or []:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def _lookup_opportunity(action: dict[str, Any]) -> dict[str, Any]:
    trade_id = str(action.get("trade_id") or "")
    trade_key = str(action.get("trade_key") or "")
    symbol = str(action.get("symbol") or "")
    for row in _load_opportunities():
        row_id = str(row.get("trade_id") or row.get("advisory_id") or row.get("id") or "")
        row_key = str(row.get("trade_key") or "")
        if trade_id and row_id == trade_id:
            return row
        if trade_key and row_key == trade_key:
            return row
        if symbol and str(row.get("symbol") or "") == symbol:
            return row
    return action.get("payload") if isinstance(action.get("payload"), dict) else {}


def _load_option_chain() -> dict[str, list[dict[str, Any]]]:
    data = _read_json(RUNTIME_DIR / "option_chain_latest.json", default={})
    return data if isinstance(data, dict) else {}


def _find_quote(row: dict[str, Any]) -> dict[str, Any]:
    tradingsymbol = str(row.get("tradingsymbol") or "")
    symbol = str(row.get("symbol") or "")
    strike = _safe_float(row.get("strike"))
    opt_type = str(row.get("option_type") or row.get("type") or "")
    chain = _load_option_chain()
    items = chain.get(symbol, []) if symbol else []
    best: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if tradingsymbol and str(item.get("tradingsymbol") or "") == tradingsymbol:
            return item
        if strike is not None and opt_type and _safe_float(item.get("strike")) == strike and str(item.get("type") or item.get("option_type") or "") == opt_type:
            best = item
    return best


def _entry_fill_price(row: dict[str, Any], action_name: str) -> tuple[float | None, str]:
    quote = _find_quote(row)
    ask = _safe_float(quote.get("ask") or quote.get("best_ask") or quote.get("entry_price_proxy_buy"))
    mid = _safe_float(quote.get("mid_price") or quote.get("mark_price"))
    ltp = _safe_float(quote.get("ltp") or quote.get("last_price"))
    entry = _safe_float(row.get("entry") or row.get("entry_price") or row.get("display_entry"))
    base = ask or mid or ltp or entry
    if base is None:
        return None, "missing_quote"
    slip = 0.0 if action_name == "FORCE" else base * DEFAULT_SLIPPAGE_PCT
    return round(base + slip, 4), "ask" if ask else "mid" if mid else "ltp" if ltp else "entry"


def _exit_quote_price(position: dict[str, Any]) -> tuple[float | None, str]:
    quote = _find_quote(position)
    bid = _safe_float(quote.get("bid") or quote.get("best_bid") or quote.get("entry_price_proxy_sell"))
    mid = _safe_float(quote.get("mid_price") or quote.get("mark_price"))
    ltp = _safe_float(quote.get("ltp") or quote.get("last_price"))
    base = bid or mid or ltp
    return (round(base, 4), "bid" if bid else "mid" if mid else "ltp") if base is not None else (None, "missing_quote")


def _derive_stop_target(row: dict[str, Any], entry_price: float, params: dict[str, float]) -> tuple[float, float, str]:
    stop = _safe_float(row.get("stop") or row.get("stop_loss") or row.get("current_stop"))
    target = _safe_float(row.get("target") or row.get("current_target"))
    source = "row_levels"
    rr = max(float(params.get("risk_reward_ratio") or 1.5), 1.0)
    if stop is None:
        stop = entry_price * (1.0 - DEFAULT_STOP_PCT)
        source = "fallback_pct"
    if target is None:
        target_pct = max(DEFAULT_TARGET_PCT, DEFAULT_STOP_PCT * rr)
        target = entry_price * (1.0 + target_pct)
        source = "fallback_pct"
    return round(stop, 4), round(target, 4), source


def _position_id(action: dict[str, Any], row: dict[str, Any]) -> str:
    return str(action.get("trade_id") or row.get("trade_id") or row.get("trade_key") or row.get("advisory_id") or f"paper-{int(_now_epoch())}")


def _process_new_actions() -> list[dict[str, Any]]:
    cursor = _load_action_cursor()
    processed_count = int(cursor.get("processed_count") or 0)
    actions = _read_jsonl(ACTION_QUEUE_PATH)
    new_actions = actions[processed_count:]
    if not new_actions:
        return []
    positions = _load_positions()
    created: list[dict[str, Any]] = []
    now = _utc_now()
    for action in new_actions:
        action_name = str(action.get("action") or "").upper()
        if action_name not in {"ENTER", "FORCE"}:
            continue
        row = _lookup_opportunity(action)
        arm = select_bandit_arm()
        params = arm["params"]
        score = float(_safe_float(row.get("score") or row.get("ranking_score") or row.get("confidence")) or 0.0)
        confidence = float(_safe_float(row.get("confidence") or row.get("global_confidence")) or 0.0)
        momentum = float(_safe_float(row.get("momentum_score") or row.get("trend_strength") or score) or 0.0)

        if action_name == "ENTER":
            if score < float(params.get("score_threshold") or 0.5):
                _record_rejection({"timestamp": _utc_now(), "reason": "bandit_score_filter", "symbol": action.get("symbol"), "score": score, "threshold": params.get("score_threshold"), "arm_id": arm["arm_id"]})
                continue
            if confidence < float(params.get("confidence_threshold") or 0.4):
                _record_rejection({"timestamp": _utc_now(), "reason": "bandit_confidence_filter", "symbol": action.get("symbol"), "confidence": confidence, "threshold": params.get("confidence_threshold"), "arm_id": arm["arm_id"]})
                continue
            if momentum < float(params.get("momentum_threshold") or 0.4):
                _record_rejection({"timestamp": _utc_now(), "reason": "bandit_momentum_filter", "symbol": action.get("symbol"), "momentum": momentum, "threshold": params.get("momentum_threshold"), "arm_id": arm["arm_id"]})
                continue
            trade_frequency = float(params.get("trade_frequency") or 1.0)
            if trade_frequency < 1.0 and random.random() > trade_frequency:
                _record_rejection({"timestamp": _utc_now(), "reason": "bandit_trade_throttle", "symbol": action.get("symbol"), "trade_frequency": trade_frequency, "arm_id": arm["arm_id"]})
                continue

        fill_price, fill_source = _entry_fill_price(row, action_name)
        if fill_price is None:
            continue
        existing = next((p for p in positions if p.get("status") == "OPEN" and (p.get("trade_id") == action.get("trade_id") or p.get("trade_key") == action.get("trade_key"))), None)
        if existing:
            continue
        stop, target, level_source = _derive_stop_target(row, fill_price, params)
        qty = int((action.get("payload") or {}).get("qty") or row.get("quantity") or DEFAULT_QTY)
        position = {
            "paper_position_id": _position_id(action, row),
            "status": "OPEN",
            "opened_at": now,
            "opened_at_epoch": _now_epoch(),
            "action": action_name,
            "trade_id": action.get("trade_id") or row.get("trade_id") or row.get("advisory_id"),
            "trade_key": action.get("trade_key") or row.get("trade_key"),
            "symbol": action.get("symbol") or row.get("symbol"),
            "tradingsymbol": row.get("tradingsymbol"),
            "option_type": row.get("option_type") or row.get("type"),
            "strike": row.get("strike"),
            "qty": qty,
            "entry_price": fill_price,
            "entry_price_source": fill_source,
            "stop_price": stop,
            "target_price": target,
            "level_source": level_source,
            "current_price": fill_price,
            "current_price_source": fill_source,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "exit_reason": None,
            "decision": row.get("decision") or row.get("final_action") or row.get("readiness"),
            "bandit_arm_id": arm["arm_id"],
            "bandit_arm_label": arm["label"],
            "adaptive_params": params,
        }
        positions.append(position)
        created.append(position)
    _save_positions(positions)
    _save_action_cursor({"processed_count": len(actions), "updated_at": _utc_now()})
    return created


def _close_position(position: dict[str, Any], price: float, reason: str, price_source: str) -> dict[str, Any]:
    entry = float(position.get("entry_price") or 0.0)
    qty = int(position.get("qty") or 1)
    realized = round((price - entry) * qty, 4)
    position["status"] = "CLOSED"
    position["closed_at"] = _utc_now()
    position["exit_price"] = round(price, 4)
    position["exit_price_source"] = price_source
    position["exit_reason"] = reason
    position["realized_pnl"] = realized
    position["unrealized_pnl"] = 0.0
    position["current_price"] = round(price, 4)
    position["current_price_source"] = price_source
    return position


def _mark_positions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positions = _load_positions()
    closed: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    now_epoch = _now_epoch()
    for position in positions:
        if position.get("status") != "OPEN":
            continue
        quote_price, quote_source = _exit_quote_price(position)
        if quote_price is None:
            updated.append(position)
            continue
        entry = float(position.get("entry_price") or 0.0)
        qty = int(position.get("qty") or 1)
        position["current_price"] = quote_price
        position["current_price_source"] = quote_source
        position["unrealized_pnl"] = round((quote_price - entry) * qty, 4)
        target = _safe_float(position.get("target_price"))
        stop = _safe_float(position.get("stop_price"))
        held_for = now_epoch - float(position.get("opened_at_epoch") or now_epoch)
        if target is not None and quote_price >= target:
            closed.append(_close_position(position, target, "TARGET_HIT", quote_source))
        elif stop is not None and quote_price <= stop:
            closed.append(_close_position(position, stop, "STOP_HIT", quote_source))
        elif held_for >= DEFAULT_TIME_EXIT_SEC:
            closed.append(_close_position(position, quote_price, "TIME_EXIT", quote_source))
        updated.append(position)
    _save_positions(positions)
    return updated, closed


def _persist_trade_history(closed_positions: list[dict[str, Any]]) -> None:
    if not closed_positions:
        return
    trades = _load_trades()
    existing_ids = {str(item.get("paper_position_id")) for item in trades if isinstance(item, dict)}
    for position in closed_positions:
        pid = str(position.get("paper_position_id"))
        if pid not in existing_ids:
            trades.insert(0, position)
    _save_trades(trades[:500])


def _recompute_pnl() -> dict[str, Any]:
    positions = _load_positions()
    trades = _load_trades()
    open_positions = [p for p in positions if p.get("status") == "OPEN"]
    closed_positions = [p for p in trades if p.get("status") == "CLOSED"]
    realized = round(sum(float(p.get("realized_pnl") or 0.0) for p in closed_positions), 4)
    unrealized = round(sum(float(p.get("unrealized_pnl") or 0.0) for p in open_positions), 4)
    win_count = sum(1 for p in closed_positions if float(p.get("realized_pnl") or 0.0) > 0)
    loss_count = sum(1 for p in closed_positions if float(p.get("realized_pnl") or 0.0) < 0)
    summary = {
        "generated_at": _utc_now(),
        "open_count": len(open_positions),
        "closed_count": len(closed_positions),
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "net_pnl": round(realized + unrealized, 4),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round((win_count / len(closed_positions)), 4) if closed_positions else None,
    }
    _write_json(PAPER_PNL_PATH, summary)
    return summary


def get_trade_diagnostics() -> dict[str, Any]:
    trades = [t for t in _load_trades() if isinstance(t, dict) and t.get("status") == "CLOSED"]
    reason_counts: dict[str, int] = {}
    symbol_counts: dict[str, int] = {}
    arm_counts: dict[str, int] = {}
    total_realized = 0.0
    win_pnls: list[float] = []
    loss_pnls: list[float] = []
    for trade in trades:
        reason = str(trade.get("exit_reason") or "UNKNOWN")
        symbol = str(trade.get("symbol") or "UNKNOWN")
        arm_id = str(trade.get("bandit_arm_id") or "UNKNOWN")
        pnl = float(trade.get("realized_pnl") or 0.0)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        arm_counts[arm_id] = arm_counts.get(arm_id, 0) + 1
        total_realized += pnl
        if pnl > 0:
            win_pnls.append(pnl)
        elif pnl < 0:
            loss_pnls.append(pnl)
    return {
        "generated_at": _utc_now(),
        "trade_count": len(trades),
        "exit_reason_counts": reason_counts,
        "top_symbols": sorted(symbol_counts.items(), key=lambda item: item[1], reverse=True)[:5],
        "arm_trade_counts": arm_counts,
        "avg_realized_pnl": round(total_realized / len(trades), 4) if trades else None,
        "avg_win": round(sum(win_pnls) / len(win_pnls), 4) if win_pnls else None,
        "avg_loss": round(sum(loss_pnls) / len(loss_pnls), 4) if loss_pnls else None,
    }


def derive_strategy_adjustments(diag: dict[str, Any]) -> dict[str, Any]:
    reasons = diag.get("exit_reason_counts") or {}
    total = max(int(diag.get("trade_count") or 0), 1)
    stop_ratio = float(reasons.get("STOP_HIT", 0)) / total
    time_ratio = float(reasons.get("TIME_EXIT", 0)) / total
    target_ratio = float(reasons.get("TARGET_HIT", 0)) / total
    avg_win = float(diag.get("avg_win") or 0.0)
    avg_loss = float(diag.get("avg_loss") or 0.0)
    bandit = get_bandit_summary()
    leader = bandit.get("leader") if isinstance(bandit, dict) else None

    adjustments: dict[str, Any] = {
        "generated_at": _utc_now(),
        "trade_count": total,
        "status": "warming_up" if total < 5 else "active",
        "bias": "neutral",
        "entry_quality": "unknown",
        "risk_reward": "unknown",
        "actions": [],
        "hints": [],
        "bandit_leader": leader.get("arm_id") if isinstance(leader, dict) else None,
        "bandit_leader_reward": leader.get("avg_reward") if isinstance(leader, dict) else None,
        "metrics": {
            "stop_ratio": round(stop_ratio, 4),
            "time_ratio": round(time_ratio, 4),
            "target_ratio": round(target_ratio, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
        },
    }

    if stop_ratio > 0.5:
        adjustments["bias"] = "overstopped"
        adjustments["entry_quality"] = "bad"
        adjustments["actions"].extend(["favor_conservative_or_momentum_arm", "reduce_aggressive_exploration"])
        adjustments["hints"].extend(["avoid breakout chasing", "reward defensive arms more heavily"])
    elif time_ratio > 0.5:
        adjustments["bias"] = "low_momentum"
        adjustments["entry_quality"] = "weak"
        adjustments["actions"].extend(["favor_momentum_focus_arm", "penalize_low_momentum_arms"])
        adjustments["hints"].append("signals are not moving fast enough")
    elif target_ratio > max(stop_ratio, time_ratio):
        adjustments["bias"] = "healthy"
        adjustments["entry_quality"] = "good"
        adjustments["actions"].append("increase_exploitation_of_best_arm")
        adjustments["hints"].append("current leading arm is relatively healthy")

    if avg_loss < 0 and abs(avg_loss) > max(abs(avg_win) * 2.0, 1.0):
        adjustments["risk_reward"] = "bad"
        adjustments["actions"].append("increase_high_rr_arm_weight")
        adjustments["hints"].append("average loss is overwhelming average win")
    elif avg_win > 0 and abs(avg_loss) <= avg_win:
        adjustments["risk_reward"] = "healthy"

    return adjustments


def update_adaptive_params(diag: dict[str, Any], params: dict[str, float]) -> dict[str, float]:
    reasons = diag.get("exit_reason_counts") or {}
    total = max(int(diag.get("trade_count") or 0), 1)
    stop_ratio = float(reasons.get("STOP_HIT", 0)) / total
    time_ratio = float(reasons.get("TIME_EXIT", 0)) / total
    avg_win = float(diag.get("avg_win") or 0.0)
    avg_loss = abs(float(diag.get("avg_loss") or 0.0))

    score_target = params["score_threshold"]
    if stop_ratio > 0.5:
        score_target = min(params["score_threshold"] + 0.05, 0.9)
    elif stop_ratio < 0.3:
        score_target = max(params["score_threshold"] - 0.03, 0.3)

    momentum_target = params["momentum_threshold"]
    if time_ratio > 0.5:
        momentum_target = min(params["momentum_threshold"] + 0.05, 0.9)
    else:
        momentum_target = max(params["momentum_threshold"] - 0.02, 0.2)

    rr_target = params["risk_reward_ratio"]
    if avg_loss > max(avg_win * 2.0, 1.0):
        rr_target = min(params["risk_reward_ratio"] + 0.2, 3.0)
    else:
        rr_target = max(params["risk_reward_ratio"] - 0.1, 1.0)

    freq_target = params["trade_frequency"]
    if stop_ratio > 0.6:
        freq_target = max(params["trade_frequency"] * 0.8, 0.3)
    else:
        freq_target = min(params["trade_frequency"] * 1.05, 1.5)

    confidence_target = params["confidence_threshold"]
    if stop_ratio > 0.5:
        confidence_target = min(params["confidence_threshold"] + 0.04, 0.9)
    elif stop_ratio < 0.25:
        confidence_target = max(params["confidence_threshold"] - 0.02, 0.2)

    params["score_threshold"] = round(_smooth(params["score_threshold"], score_target), 4)
    params["momentum_threshold"] = round(_smooth(params["momentum_threshold"], momentum_target), 4)
    params["risk_reward_ratio"] = round(_smooth(params["risk_reward_ratio"], rr_target), 4)
    params["trade_frequency"] = round(_smooth(params["trade_frequency"], freq_target), 4)
    params["confidence_threshold"] = round(_smooth(params["confidence_threshold"], confidence_target), 4)
    return params


def _save_learning(adjustments: dict[str, Any]) -> None:
    _write_json(PAPER_LEARNING_PATH, adjustments)


def get_learning() -> dict[str, Any]:
    data = _read_json(PAPER_LEARNING_PATH, default={})
    return data if isinstance(data, dict) else {}


def run_paper_cycle() -> dict[str, Any]:
    created = _process_new_actions()
    _, closed = _mark_positions()
    _persist_trade_history(closed)
    bandit_update = update_bandit_rewards()
    pnl = _recompute_pnl()
    diagnostics = get_trade_diagnostics()
    learning = derive_strategy_adjustments(diagnostics)
    _save_learning(learning)
    params = load_adaptive_params()
    params = update_adaptive_params(diagnostics, params)
    save_adaptive_params(params)
    return {
        "generated_at": _utc_now(),
        "created_positions": len(created),
        "closed_positions": len(closed),
        "summary": pnl,
        "learning": learning,
        "adaptive_params": params,
        "bandit": bandit_update.get("bandit"),
    }


def get_positions() -> list[dict[str, Any]]:
    return _load_positions()


def get_trade_history() -> list[dict[str, Any]]:
    return _load_trades()


def get_pnl_summary() -> dict[str, Any]:
    return _read_json(PAPER_PNL_PATH, default={})
