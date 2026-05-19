from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_EXECUTION_MODES = {"SIM", "PAPER", "LIVE"}
ENGINE_ROOT_ENV_VARS = ("ALGOTRADIFY_ENGINE_ROOT", "TRADEBOT_ROOT", "CORE_BOT_ROOT")
REQUIRE_NATIVE_ENV = "ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME"
ALLOW_EXTERNAL_ENV = "ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME"
NATIVE_MANIFEST = "RUNTIME_SOURCE_MANIFEST.json"
NATIVE_ENTRYPOINT_SNAPSHOT = "runtime_native/tradebot_main.py"
EXTERNAL_RUNTIME_DEPRECATION_MESSAGE = (
    "external runtime fallback is deprecated; use native algotradify runtime or set "
    "ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME=true for temporary compatibility"
)


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


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def native_runtime_required() -> bool:
    return _env_flag(REQUIRE_NATIVE_ENV)


def external_runtime_allowed(*, default: bool = False) -> bool:
    if native_runtime_required():
        return False
    return _env_flag(ALLOW_EXTERNAL_ENV, default=default)


def external_runtime_deprecated() -> bool:
    return True


def is_tradebot_compatible_root(path: Path) -> bool:
    root = path.expanduser().resolve()
    return (root / "main.py").is_file() and (root / "core").is_dir() and (root / "config").is_dir()


def is_native_runtime_source_root(path: Path) -> bool:
    root = path.expanduser().resolve()
    return (
        (root / "main.py").is_file()
        and (root / "core").is_dir()
        and (root / "config").is_dir()
        and (root / NATIVE_MANIFEST).is_file()
        and (root / NATIVE_ENTRYPOINT_SNAPSHOT).is_file()
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _root_main_is_wrapper(root: Path) -> bool:
    text = _read_text(root / "main.py")
    markers = (
        "spec_from_file_location",
        "_load_runtime_main",
        "Tradebot-compatible runtime",
        "runtime_root = resolve_runtime_root()",
        "Algotradify runtime bootstrap failed",
    )
    return any(marker in text for marker in markers)


def runtime_ownership_for_root(root: Path) -> str:
    resolved = root.expanduser().resolve()
    native_source_present = is_native_runtime_source_root(resolved)
    if native_source_present and not _root_main_is_wrapper(resolved):
        return "NATIVE"
    if native_source_present:
        return "NATIVE_SOURCE_IMPORTED_PENDING_MAIN_PROMOTION"
    return "WRAPPER_OR_EXTERNAL_COMPATIBLE"


def candidate_runtime_roots(
    *,
    base_repo_root: Path | None = None,
    home: Path | None = None,
    include_native_root: bool | None = None,
    allow_external: bool | None = None,
) -> list[Path]:
    root = (base_repo_root or repo_root()).expanduser().resolve()
    home_root = (home or Path.home()).expanduser().resolve()
    include_native = is_native_runtime_source_root(root) if include_native_root is None else include_native_root
    external_ok = external_runtime_allowed(default=False) if allow_external is None else allow_external
    candidates: list[Path] = []

    if include_native:
        candidates.append(root)

    if external_ok:
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


def resolve_runtime_root(
    *,
    base_repo_root: Path | None = None,
    home: Path | None = None,
    require_native: bool | None = None,
    include_native_root: bool | None = None,
    allow_external: bool | None = None,
) -> Path | None:
    root = (base_repo_root or repo_root()).expanduser().resolve()
    native_required = native_runtime_required() if require_native is None else require_native
    if native_required:
        return root if is_native_runtime_source_root(root) else None

    for candidate in candidate_runtime_roots(
        base_repo_root=root,
        home=home,
        include_native_root=include_native_root,
        allow_external=allow_external,
    ):
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
        selected_engine = root if is_native_runtime_source_root(root) else root / ".runtime"
    selected_engine = selected_engine.expanduser().resolve()

    if selected_engine == root and is_native_runtime_source_root(root):
        return (root / ".runtime").resolve()

    candidates = [
        selected_engine / ".runtime",
        selected_engine / "runtime",
        root / ".runtime",
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


def _check_native_source(root: Path) -> list[PreflightCheck]:
    native_present = is_native_runtime_source_root(root)
    main_wrapper = _root_main_is_wrapper(root)
    return [
        PreflightCheck(
            name="native_runtime_source.present",
            status="PASS" if native_present else "FAIL",
            message=(
                "native runtime source markers present"
                if native_present
                else "native runtime source markers missing: main.py, core/, config/, manifest, or runtime_native/tradebot_main.py"
            ),
            path=str(root),
            metadata={
                "main": (root / "main.py").is_file(),
                "core": (root / "core").is_dir(),
                "config": (root / "config").is_dir(),
                "manifest": (root / NATIVE_MANIFEST).is_file(),
                "entrypoint_snapshot": (root / NATIVE_ENTRYPOINT_SNAPSHOT).is_file(),
            },
        ),
        PreflightCheck(
            name="native_runtime_main.promoted",
            status="WARN" if native_present and main_wrapper else ("PASS" if native_present else "FAIL"),
            message=(
                "root main.py is still wrapper; promotion deferred to Runtime Correction PR 5"
                if native_present and main_wrapper
                else "root main.py is native runtime entrypoint"
                if native_present
                else "root main.py promotion cannot be evaluated without native source"
            ),
            path=str(root / "main.py"),
            metadata={"root_main_is_wrapper": main_wrapper},
        ),
    ]


def _check_external_runtime_deprecation(*, external_ok: bool, runtime_root: Path | None, root: Path) -> PreflightCheck:
    external_used = bool(runtime_root and runtime_root.expanduser().resolve() != root.expanduser().resolve())
    if external_used:
        status = "WARN"
        message = "external runtime fallback is enabled and currently selected; this is temporary compatibility only"
    elif external_ok:
        status = "WARN"
        message = "external runtime fallback is explicitly enabled but native runtime is selected"
    else:
        status = "PASS"
        message = "external runtime fallback disabled by default"
    return PreflightCheck(
        name="external_runtime_fallback.deprecated",
        status=status,
        message=message,
        metadata={
            "deprecated": True,
            "external_runtime_allowed": bool(external_ok),
            "external_runtime_used": external_used,
            "opt_in_env": ALLOW_EXTERNAL_ENV,
            "deprecation_message": EXTERNAL_RUNTIME_DEPRECATION_MESSAGE,
        },
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
    native_required = native_runtime_required()
    external_ok = external_runtime_allowed(default=False)
    ownership = runtime_ownership_for_root(root)
    native_source_present = is_native_runtime_source_root(root)
    candidates = candidate_runtime_roots(
        base_repo_root=root,
        home=home,
        include_native_root=True if native_source_present else native_required,
        allow_external=external_ok,
    )
    runtime_root = resolve_runtime_root(
        base_repo_root=root,
        home=home,
        require_native=native_required,
        include_native_root=True if native_source_present else native_required,
        allow_external=external_ok,
    )

    checks.append(_check_external_runtime_deprecation(external_ok=external_ok, runtime_root=runtime_root, root=root))

    if native_required or native_source_present:
        checks.extend(_check_native_source(root))

    if runtime_root is None:
        checks.append(
            PreflightCheck(
                name="runtime_root.resolved",
                status="FAIL",
                message=(
                    "native runtime source root required but missing"
                    if native_required
                    else "no native runtime root found; external fallback is disabled unless explicitly enabled"
                ),
                metadata={"checked_paths": [str(path.expanduser()) for path in candidates]},
            )
        )
        artifact_root = runtime_artifact_root(engine_root=root if native_source_present else root / ".runtime", base_repo_root=root)
    else:
        external_runtime_used = runtime_root != root
        checks.append(
            PreflightCheck(
                name="runtime_root.resolved",
                status="PASS",
                message=(
                    "native runtime source root selected"
                    if runtime_root == root
                    else "deprecated external Tradebot-compatible runtime root selected"
                ),
                path=str(runtime_root),
                metadata={
                    "checked_paths": [str(path.expanduser()) for path in candidates],
                    "external_runtime_used": external_runtime_used,
                    "native_required": native_required,
                },
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
    external_runtime_used = bool(runtime_root and runtime_root != root)

    return {
        "status": status,
        "runtime_root": str(runtime_root) if runtime_root else None,
        "runtime_artifact_root": str(artifact_root) if 'artifact_root' in locals() else None,
        "runtime_ownership": ownership,
        "native_required": native_required,
        "native_source_present": native_source_present,
        "native_main_promoted": native_source_present and not _root_main_is_wrapper(root),
        "external_runtime_allowed": external_ok,
        "external_runtime_deprecated": True,
        "external_runtime_deprecation_message": EXTERNAL_RUNTIME_DEPRECATION_MESSAGE,
        "external_runtime_used": external_runtime_used,
        "checked_at_source": "runtime_contract.run_preflight",
        "summary": {
            "pass_count": sum(1 for check in checks if check.status == "PASS"),
            "warn_count": warn_count,
            "fail_count": fail_count,
        },
        "checks": serialized_checks,
    }