from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_EXECUTION_MODES = {"SIM", "PAPER", "LIVE"}
ENGINE_ROOT_ENV_VARS = ("ALGOTRADIFY_ENGINE_ROOT", "TRADEBOT_ROOT", "CORE_BOT_ROOT")


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    message: str
    path: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "message": self.message,
        }
        if self.path is not None:
            payload["path"] = self.path
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def is_tradebot_compatible_root(path: Path) -> bool:
    root = path.expanduser().resolve()
    return (root / "main.py").is_file() and (root / "core").is_dir() and (root / "config").is_dir()


def candidate_runtime_roots(*, base_repo_root: Path | None = None, home: Path | None = None) -> list[Path]:
    root = (base_repo_root or repo_root()).expanduser().resolve()
    home_root = (home or Path.home()).expanduser().resolve()
    candidates: list[Path] = []

    for env_name in ENGINE_ROOT_ENV_VARS:
        configured = str(os.getenv(env_name, "")).strip()
        if configured:
            candidates.append(Path(configured))

    candidates.extend(
        [
            root / "core_bot",
            root.parent / "tradebot",
            home_root / "tradebot",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            key = str(candidate.expanduser().resolve())
        except Exception:
            key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_runtime_root(*, base_repo_root: Path | None = None, home: Path | None = None) -> Path | None:
    for candidate in candidate_runtime_roots(base_repo_root=base_repo_root, home=home):
        if is_tradebot_compatible_root(candidate):
            return candidate.expanduser().resolve()
    return None


def runtime_artifact_root(*, engine_root: Path | None = None, base_repo_root: Path | None = None) -> Path:
    configured = str(os.getenv("CORE_BOT_RUNTIME_ROOT", "")).strip()
    if configured:
        return Path(configured).expanduser().resolve()

    root = (base_repo_root or repo_root()).expanduser().resolve()
    selected_engine = engine_root or resolve_runtime_root(base_repo_root=root)
    if selected_engine is None:
        selected_engine = root / "core_bot"
    selected_engine = selected_engine.expanduser().resolve()

    candidates = [
        selected_engine / ".runtime",
        selected_engine / "runtime",
        root / "core_bot" / ".runtime",
        root / "core_bot" / "runtime",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (selected_engine / ".runtime").resolve()


def _check_required_path(root: Path, relative: str, *, directory: bool = False) -> PreflightCheck:
    target = root / relative
    exists = target.is_dir() if directory else target.is_file()
    return PreflightCheck(
        name=f"runtime_root.{relative}",
        status="PASS" if exists else "FAIL",
        message=f"required {'directory' if directory else 'file'} {'exists' if exists else 'missing'}: {relative}",
        path=str(target),
    )


def _check_runtime_artifact_root(path: Path) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    exists = path.exists()
    if not exists:
        try:
            path.mkdir(parents=True, exist_ok=True)
            exists = True
            created = True
        except Exception as exc:
            checks.append(
                PreflightCheck(
                    name="runtime_artifact_root.writable",
                    status="FAIL",
                    message=f"runtime artifact root cannot be created: {type(exc).__name__}: {exc}",
                    path=str(path),
                )
            )
            return checks
    else:
        created = False

    checks.append(
        PreflightCheck(
            name="runtime_artifact_root.exists",
            status="PASS" if exists else "FAIL",
            message="runtime artifact root exists" if exists else "runtime artifact root missing",
            path=str(path),
            metadata={"created": created},
        )
    )

    try:
        probe = path / ".algotradify_preflight_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks.append(
            PreflightCheck(
                name="runtime_artifact_root.writable",
                status="PASS",
                message="runtime artifact root is writable",
                path=str(path),
            )
        )
    except Exception as exc:
        checks.append(
            PreflightCheck(
                name="runtime_artifact_root.writable",
                status="FAIL",
                message=f"runtime artifact root is not writable: {type(exc).__name__}: {exc}",
                path=str(path),
            )
        )
    return checks


def _check_execution_mode() -> PreflightCheck:
    raw = str(os.getenv("EXECUTION_MODE") or os.getenv("TRADING_MODE") or "SIM").strip().upper()
    valid = raw in VALID_EXECUTION_MODES
    return PreflightCheck(
        name="execution_mode.valid",
        status="PASS" if valid else "FAIL",
        message=f"execution mode {'valid' if valid else 'invalid'}: {raw or 'unset'}",
        metadata={"execution_mode": raw or None, "valid_modes": sorted(VALID_EXECUTION_MODES)},
    )


def _check_token_expectation(runtime_root: Path, artifact_root: Path) -> PreflightCheck:
    possible_paths = [
        artifact_root / "kite_access_token",
        artifact_root / "kite" / "access_token",
        runtime_root / ".runtime" / "kite_access_token",
        runtime_root / "runtime" / "kite_access_token",
    ]
    existing = [path for path in possible_paths if path.exists()]
    live_like = str(os.getenv("EXECUTION_MODE") or os.getenv("TRADING_MODE") or "SIM").strip().upper() in {"LIVE", "PAPER"}
    status = "PASS" if existing else ("FAIL" if live_like else "WARN")
    return PreflightCheck(
        name="broker_token.available",
        status=status,
        message=(
            "broker token candidate found"
            if existing
            else "broker token not found; required for PAPER/LIVE and optional for SIM"
        ),
        metadata={
            "checked_paths": [str(path) for path in possible_paths],
            "existing_paths": [str(path) for path in existing],
            "live_like_mode": live_like,
        },
    )


def run_preflight(*, base_repo_root: Path | None = None, home: Path | None = None, create_runtime_dirs: bool = True) -> dict[str, Any]:
    root = (base_repo_root or repo_root()).expanduser().resolve()
    checks: list[PreflightCheck] = []
    candidates = candidate_runtime_roots(base_repo_root=root, home=home)
    runtime_root = resolve_runtime_root(base_repo_root=root, home=home)

    if runtime_root is None:
        checks.append(
            PreflightCheck(
                name="runtime_root.resolved",
                status="FAIL",
                message="no Tradebot-compatible runtime root found",
                metadata={"checked_paths": [str(path.expanduser()) for path in candidates]},
            )
        )
        artifact_root = runtime_artifact_root(engine_root=root / "core_bot", base_repo_root=root)
    else:
        checks.append(
            PreflightCheck(
                name="runtime_root.resolved",
                status="PASS",
                message="Tradebot-compatible runtime root found",
                path=str(runtime_root),
                metadata={"checked_paths": [str(path.expanduser()) for path in candidates]},
            )
        )
        checks.extend(
            [
                _check_required_path(runtime_root, "main.py"),
                _check_required_path(runtime_root, "core", directory=True),
                _check_required_path(runtime_root, "config", directory=True),
                _check_required_path(runtime_root, "requirements.txt"),
            ]
        )
        artifact_root = runtime_artifact_root(engine_root=runtime_root, base_repo_root=root)
        if create_runtime_dirs:
            checks.extend(_check_runtime_artifact_root(artifact_root))
        checks.append(_check_token_expectation(runtime_root, artifact_root))

    checks.append(_check_execution_mode())

    serialized_checks = [check.to_dict() for check in checks]
    fail_count = sum(1 for check in checks if check.status == "FAIL")
    warn_count = sum(1 for check in checks if check.status == "WARN")
    status = "FAIL" if fail_count else ("WARN" if warn_count else "PASS")

    return {
        "status": status,
        "runtime_root": str(runtime_root) if runtime_root else None,
        "runtime_artifact_root": str(artifact_root) if 'artifact_root' in locals() else None,
        "checked_at_source": "runtime_contract.run_preflight",
        "summary": {
            "pass_count": sum(1 for check in checks if check.status == "PASS"),
            "warn_count": warn_count,
            "fail_count": fail_count,
        },
        "checks": serialized_checks,
    }
