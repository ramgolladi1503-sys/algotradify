#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import stat
import sys
import urllib.parse
from pathlib import Path


MIN_TOKEN_LENGTH = 20


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def clean(value: str | None) -> str:
    return str(value or "").strip()


def tail4(value: str) -> str:
    text = clean(value)
    return text[-4:] if len(text) >= 4 else text


def extract_request_token(value: str) -> str:
    text = clean(value)
    if not text:
        return ""
    if "request_token=" not in text:
        return text
    parsed = urllib.parse.urlparse(text)
    query = urllib.parse.parse_qs(parsed.query)
    return clean((query.get("request_token") or [""])[0])


def write_access_token(path: Path, access_token: str) -> None:
    token = clean(access_token)
    if len(token) < MIN_TOKEN_LENGTH:
        raise SystemExit(f"[KITE_LOGIN][ERROR] access_token_too_short len={len(token)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token + "\n", encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    print(f"[KITE_LOGIN] token_written path={path} len={len(token)} tail4={tail4(token)}")


def build_login_url(api_key: str) -> str:
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:
        raise SystemExit("[KITE_LOGIN][ERROR] kiteconnect package unavailable; run pip install -r requirements.txt") from exc
    return KiteConnect(api_key=api_key).login_url()


def generate_access_token(api_key: str, api_secret: str, request_token: str) -> str:
    try:
        from kiteconnect import KiteConnect
    except Exception as exc:
        raise SystemExit("[KITE_LOGIN][ERROR] kiteconnect package unavailable; run pip install -r requirements.txt") from exc
    kite = KiteConnect(api_key=api_key)
    try:
        session = kite.generate_session(request_token, api_secret=api_secret)
    except Exception as exc:
        raise SystemExit(f"[KITE_LOGIN][ERROR] generate_session_failed type={type(exc).__name__} message={exc}") from exc
    access_token = clean(session.get("access_token"))
    if not access_token:
        raise SystemExit("[KITE_LOGIN][ERROR] access_token_missing_from_session")
    return access_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-only Kite login helper for Algotradify")
    parser.add_argument("--request-token", default=os.getenv("KITE_REQUEST_TOKEN"), help="Kite request_token or full redirect URL")
    parser.add_argument("--token-path", default=os.getenv("KITE_ACCESS_TOKEN_FILE") or str(repo_root() / ".runtime" / "kite_access_token"))
    parser.add_argument("--print-login-url-only", action="store_true", help="Print login URL and exit without writing a token")
    args = parser.parse_args(argv)

    api_key = clean(os.getenv("KITE_API_KEY"))
    api_secret = clean(os.getenv("KITE_API_SECRET"))
    if not api_key:
        raise SystemExit("[KITE_LOGIN][ERROR] KITE_API_KEY missing")
    if args.print_login_url_only:
        print(build_login_url(api_key))
        return 0
    if not api_secret:
        raise SystemExit("[KITE_LOGIN][ERROR] KITE_API_SECRET missing")

    login_url = build_login_url(api_key)
    print("[KITE_LOGIN] Open this URL in your browser, complete Kite login, then paste request_token or the full redirected URL.")
    print(f"[KITE_LOGIN] login_url={login_url}")

    request_token = extract_request_token(clean(args.request_token) or input("request_token_or_redirect_url: "))
    if not request_token:
        raise SystemExit("[KITE_LOGIN][ERROR] request_token missing")
    print(f"[KITE_LOGIN] request_token_captured len={len(request_token)} tail4={tail4(request_token)}")

    access_token = generate_access_token(api_key=api_key, api_secret=api_secret, request_token=request_token)
    write_access_token(Path(args.token_path).expanduser().resolve(), access_token)
    print("[KITE_LOGIN] login_complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
