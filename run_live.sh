#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_PATH="${KITE_ACCESS_TOKEN_FILE:-$ROOT_DIR/.runtime/kite_access_token}"

usage() {
  cat <<'EOF'
Usage:
  ./run_live.sh --validate-only
  ./run_live.sh --login-only
  ./run_live.sh --start --i-understand-live-risk

Purpose:
  Native guarded LIVE operator entrypoint for algotradify.

Safety:
  - This script never defaults to LIVE startup.
  - --start requires --i-understand-live-risk.
  - DRY_RUN=true is rejected for LIVE startup.
  - EXECUTION_MODE and TRADING_MODE are forced to LIVE only after gates pass.
  - Root run_live.sh is operator-only; strategy/broker behavior remains in main.py safety gates.

Options:
  --validate-only             Run runtime preflight and token-file presence checks, then exit.
  --login-only                Run local Kite login helper, then exit.
  --start                     Start native main.py in LIVE mode after explicit confirmation.
  --i-understand-live-risk    Required with --start.
  -h, --help                  Show this help.
EOF
}

START=0
VALIDATE_ONLY=0
LOGIN_ONLY=0
CONFIRM_LIVE=0

for arg in "$@"; do
  case "$arg" in
    --start) START=1 ;;
    --validate-only) VALIDATE_ONLY=1 ;;
    --login-only) LOGIN_ONLY=1 ;;
    --i-understand-live-risk) CONFIRM_LIVE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[RUN_LIVE][ERROR] unknown_arg=$arg"; usage; exit 2 ;;
  esac
done

selected_count=$((START + VALIDATE_ONLY + LOGIN_ONLY))
if [[ "$selected_count" -ne 1 ]]; then
  echo "[RUN_LIVE][ERROR] choose exactly one of --validate-only, --login-only, or --start"
  usage
  exit 2
fi

ensure_runtime_dirs() {
  mkdir -p "$ROOT_DIR/.runtime" "$ROOT_DIR/.runtime/logs" "$ROOT_DIR/.runtime/locks" "$ROOT_DIR/.runtime/db"
}

preflight() {
  echo "[RUN_LIVE] repo_root=$ROOT_DIR"
  echo "[RUN_LIVE] token_path=$TOKEN_PATH"
  ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME=true python "$ROOT_DIR/scripts/preflight_runtime.py" --json --no-create-runtime-dirs
}

validate_token_file_present() {
  if [[ ! -f "$TOKEN_PATH" ]]; then
    echo "[RUN_LIVE][ERROR] token_file_missing path=$TOKEN_PATH"
    echo "[RUN_LIVE] Run: ./run_live.sh --login-only"
    exit 12
  fi
  local token
  token="$(tr -d ' \n\r\t' < "$TOKEN_PATH")"
  if [[ "${#token}" -lt 20 ]]; then
    echo "[RUN_LIVE][ERROR] token_file_too_short path=$TOKEN_PATH len=${#token}"
    exit 12
  fi
  export KITE_ACCESS_TOKEN="$token"
  echo "[RUN_LIVE] token_file_present len=${#KITE_ACCESS_TOKEN} tail4=${KITE_ACCESS_TOKEN: -4}"
}

run_login_only() {
  ensure_runtime_dirs
  if [[ -z "${KITE_API_KEY:-}" || -z "${KITE_API_SECRET:-}" ]]; then
    echo "[RUN_LIVE][ERROR] KITE_API_KEY and KITE_API_SECRET are required for --login-only"
    exit 1
  fi
  echo "[RUN_LIVE] launching local Kite login helper"
  python "$ROOT_DIR/scripts/kite_autologin_localhost.py"
  validate_token_file_present
  echo "[RUN_LIVE] login_only_complete"
}

if [[ "$VALIDATE_ONLY" -eq 1 ]]; then
  ensure_runtime_dirs
  preflight
  validate_token_file_present
  echo "[RUN_LIVE] validate_only_complete"
  exit 0
fi

if [[ "$LOGIN_ONLY" -eq 1 ]]; then
  run_login_only
  exit 0
fi

if [[ "$START" -eq 1 ]]; then
  if [[ "$CONFIRM_LIVE" -ne 1 ]]; then
    echo "[RUN_LIVE][FATAL] --start requires --i-understand-live-risk"
    exit 2
  fi
  if [[ "${DRY_RUN:-false}" =~ ^([Tt][Rr][Uu][Ee]|1|[Yy][Ee]?[Ss])$ ]]; then
    echo "[RUN_LIVE][FATAL] DRY_RUN=true is incompatible with LIVE startup"
    exit 2
  fi
  ensure_runtime_dirs
  preflight
  validate_token_file_present
  export TRADING_MODE="LIVE"
  export EXECUTION_MODE="LIVE"
  export ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME="true"
  echo "[RUN_LIVE] starting native main.py with EXECUTION_MODE=$EXECUTION_MODE TRADING_MODE=$TRADING_MODE"
  exec python "$ROOT_DIR/main.py"
fi
