from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_native_runtime_required_paths_are_tracked_source():
    assert (ROOT / "core").is_dir()
    assert (ROOT / "config").is_dir()
    assert (ROOT / "dashboard").is_dir()
    assert (ROOT / "runtime_native" / "tradebot_main.py").is_file()
    assert (ROOT / "runtime_native" / "tradebot_run_live.sh").is_file()
    assert (ROOT / "runtime_native" / "tradebot_requirements.txt").is_file()


def test_runtime_source_manifest_exists_and_is_safe():
    payload = json.loads((ROOT / "RUNTIME_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))

    assert payload["import_mode"] == "native_tracked_source"
    assert payload["imported_required_markers"]["main.py"] is True
    assert payload["imported_required_markers"]["core"] is True
    assert payload["imported_required_markers"]["config"] is True

    safe_flags = payload["safe_flags"]
    assert safe_flags["source_imported"] is True
    assert safe_flags["runtime_behavior_changed"] is False
    assert safe_flags["is_order_action"] is False
    assert safe_flags["broker_api_called"] is False
    assert safe_flags["real_order_id"] is None
    assert safe_flags["live_mode_touched"] is False


def test_native_import_does_not_replace_root_main_or_run_live():
    root_main = ROOT / "main.py"
    root_run_live = ROOT / "run_live.sh"

    assert root_main.is_file()
    assert not root_run_live.exists()

    main_text = root_main.read_text(encoding="utf-8", errors="ignore")
    assert "spec_from_file_location" in main_text or "resolve_runtime_root" in main_text


def test_import_does_not_include_secret_or_runtime_artifacts():
    forbidden_names = {".env", "kite_access_token"}
    forbidden_suffixes = {".token", ".secret", ".sqlite", ".sqlite3", ".db", ".pyc"}
    forbidden_name_fragments = {".bak"}
    forbidden_parts = {".runtime", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

    imported_roots = [
        ROOT / "core",
        ROOT / "config",
        ROOT / "dashboard",
        ROOT / "ml",
        ROOT / "models",
        ROOT / "rl",
        ROOT / "fixtures",
        ROOT / "runtime_native",
    ]

    strategy_imports = [
        ROOT / "strategies" / "banknifty_intraday.py",
        ROOT / "strategies" / "ensemble.py",
        ROOT / "strategies" / "nifty_intraday.py",
        ROOT / "strategies" / "position_sizer.py",
        ROOT / "strategies" / "pro_layer",
        ROOT / "strategies" / "risk_manager.py",
        ROOT / "strategies" / "sensex_intraday.py",
        ROOT / "strategies" / "soft_signal.py",
        ROOT / "strategies" / "trade_builder.py",
        ROOT / "strategies" / "vwap_orb.py",
        ROOT / "strategies" / "zero_hero.py",
    ]

    paths_to_scan = []
    for root in imported_roots + strategy_imports:
        if root.is_file():
            paths_to_scan.append(root)
        elif root.is_dir():
            paths_to_scan.extend(root.rglob("*"))

    assert paths_to_scan, "expected imported runtime paths to be scanned"

    for path in paths_to_scan:
        rel = path.relative_to(ROOT).as_posix()
        assert path.name not in forbidden_names, rel
        assert not any(fragment in path.name for fragment in forbidden_name_fragments), rel
        assert not any(path.name.endswith(suffix) for suffix in forbidden_suffixes), rel
        assert not any(part in rel.split("/") for part in forbidden_parts), rel
