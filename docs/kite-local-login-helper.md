# Kite Local Login Helper

## Purpose

`run_live.sh --login-only` requires `scripts/kite_autologin_localhost.py` to create the local Kite access token file.

This helper is intentionally local and manual. It does not start the trading runtime, does not place orders, does not mutate live mode, and does not expose raw tokens or API secrets.

## Required environment

The operator must set Kite API credentials in the shell before running login. Do not commit them, paste them into chat, or store them in tracked files.

## Usage through run_live.sh

```bash
./run_live.sh --login-only
./run_live.sh --validate-only
```

The login helper prints the Kite login URL. Open it in a browser, complete the login, then paste either the request token or the full redirected URL containing the request token.

## Direct helper usage

Print login URL only:

```bash
python scripts/kite_autologin_localhost.py --print-login-url-only
```

Generate and write token using an already captured request token:

```bash
python scripts/kite_autologin_localhost.py --request-token "$KITE_REQUEST_TOKEN"
```

## Token output

The helper writes only this local runtime file:

```text
.runtime/kite_access_token
```

It sets the file mode to `0600` where supported.

The helper may print token length and tail4 for debugging, but must not print the raw access token or API secret.

## Safety boundary

This helper must not:

- place orders
- modify orders
- cancel orders
- start live runtime
- set execution mode
- set trading mode
- print raw access token
- print API secret
- write token anywhere except the configured token file

## Validation

```bash
python -m pytest tests/test_kite_autologin_helper_contract.py -q
python scripts/runtime_migration_lock.py
./run_live.sh --login-only
./run_live.sh --validate-only
```
