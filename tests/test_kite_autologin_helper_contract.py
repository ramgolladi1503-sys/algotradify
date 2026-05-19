from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "kite_autologin_localhost.py"


def _load_helper():
    spec = importlib.util.spec_from_file_location("kite_autologin_localhost", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_kite_login_helper_exists_and_is_local_only():
    text = HELPER.read_text(encoding="utf-8")

    assert HELPER.is_file()
    assert "KiteConnect" in text
    assert "generate_session" in text
    assert ".runtime" in text
    assert "kite_access_token" in text
    assert "submit_order" not in text
    assert "place_order" not in text
    assert "modify_order" not in text
    assert "cancel_order" not in text
    assert "EXECUTION_MODE" not in text
    assert "TRADING_MODE" not in text
    assert "LIVE" not in text


def test_extract_request_token_accepts_raw_token_or_redirect_url():
    helper = _load_helper()

    assert helper.extract_request_token("abc123") == "abc123"
    assert helper.extract_request_token("https://example.local/callback?status=success&request_token=req_123&action=login") == "req_123"
    assert helper.extract_request_token("") == ""


def test_write_access_token_writes_0600_without_printing_raw_token(tmp_path, capsys):
    helper = _load_helper()
    token_path = tmp_path / ".runtime" / "kite_access_token"
    token = "access_token_abcdefghijklmnopqrstuvwxyz"

    helper.write_access_token(token_path, token)

    assert token_path.read_text(encoding="utf-8") == token + "\n"
    assert oct(token_path.stat().st_mode & 0o777) == "0o600"
    captured = capsys.readouterr().out
    assert "token_written" in captured
    assert "tail4=wxyz" in captured
    assert token not in captured


def test_write_access_token_rejects_short_token(tmp_path):
    helper = _load_helper()
    token_path = tmp_path / ".runtime" / "kite_access_token"

    try:
        helper.write_access_token(token_path, "short")
    except SystemExit as exc:
        assert "access_token_too_short" in str(exc)
    else:
        raise AssertionError("short token should fail")


def test_helper_text_does_not_print_api_secret_or_raw_access_token():
    text = HELPER.read_text(encoding="utf-8")

    assert "api_secret=" in text
    assert "print(api_secret" not in text
    assert "print(access_token" not in text
    assert "print(f\"{access_token}" not in text
    assert "raw_token" not in text


def test_run_live_references_existing_login_helper():
    run_live = (ROOT / "run_live.sh").read_text(encoding="utf-8")

    assert "scripts/kite_autologin_localhost.py" in run_live
    assert HELPER.is_file()
