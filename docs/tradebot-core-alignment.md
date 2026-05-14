# Tradebot core alignment

Goal: make Algotradify run against the same Tradebot engine behavior without touching `ramgolladi1503-sys/tradebot` `main`.

## Source of truth

`ramgolladi1503-sys/tradebot` `main` remains the trading-engine source of truth until Algotradify owns the full engine directly.

Algotradify should either:

1. Use a local read-only Tradebot checkout through `ALGOTRADIFY_ENGINE_ROOT`, `TRADEBOT_ROOT`, or `CORE_BOT_ROOT`, or
2. Embed a sanitized copy of Tradebot into `algotradify/core_bot/` using the sync utility.

## Canonical runtime command

Use this as the primary command:

```bash
python main.py
```

Compatibility command for older scripts:

```bash
python -m runner.live_wrapper
```

The wrapper must delegate to `main.py`. It must not reimplement engine-root resolution.

## Engine root resolution

Both `main.py` and `api/server.py` must use the same engine-root priority:

1. `ALGOTRADIFY_ENGINE_ROOT`
2. `TRADEBOT_ROOT`
3. `CORE_BOT_ROOT`
4. `algotradify/core_bot`
5. `../tradebot`
6. `~/tradebot`

A compatible runtime root must contain:

- `main.py`
- `core/`
- `config/`

## External checkout mode

Use this when you want zero copied engine code inside Algotradify:

```bash
export ALGOTRADIFY_ENGINE_ROOT=/absolute/path/to/tradebot
python main.py
```

Compatibility variables also work:

```bash
export TRADEBOT_ROOT=/absolute/path/to/tradebot
python main.py
```

```bash
export CORE_BOT_ROOT=/absolute/path/to/tradebot
python main.py
```

The selected Tradebot root is placed first on `sys.path` because Tradebot uses absolute imports such as `from config import ...` and `from core...`.

## Embedded sync mode

Use this when Algotradify must be self-contained:

```bash
python scripts/sync_tradebot_core.py --source ../tradebot --force
python main.py
```

The sync utility copies Tradebot into `algotradify/core_bot/`, while excluding:

- `.git/`
- `.runtime/`
- `runtime/`
- `logs/`
- `.env` files
- token/secret files
- Python caches
- local DB files
- large local CSV/parquet artifacts under `data/`

It writes `core_bot/TRADEBOT_SOURCE.json` with source path, remote, branch, commit, sync time, copied file count, and excluded patterns.

## Runtime artifact resolution

The API bridge resolves runtime data in this order:

1. `CORE_BOT_RUNTIME_ROOT`
2. selected engine root `.runtime`
3. selected engine root `runtime`
4. `algotradify/core_bot/.runtime`
5. `algotradify/core_bot/runtime`

## Redis event compatibility

Defaults remain compatible with Tradebot:

- Redis host: `localhost`
- Redis port: `6379`
- Redis channel: `tradebot_events`

Optional overrides:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export TRADEBOT_REDIS_CHANNEL=tradebot_events
```

## Local verification

```bash
python main.py
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
curl http://localhost:8000/runtime/health
curl http://localhost:8000/runtime/snapshot
curl 'http://localhost:8000/opportunities?limit=20'
```

## Important rule

Do not edit Tradebot through Algotradify work. If engine behavior needs to change, change it in Tradebot first, verify it, then re-sync or point `ALGOTRADIFY_ENGINE_ROOT`/`TRADEBOT_ROOT` to that verified checkout.
