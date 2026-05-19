#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LockCheck:
    name: str
    status: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        payload: dict[str, str | None] = {
            "name": self.name,
            "status": self.status,
            "message": self.message,
        }
        if self.path is not None:
            payload["path"] = self.path
        return payload


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _exists(path: Path, *, directory: bool = False) -> LockCheck:
    ok = path.is_dir() if directory else path.is_file()
    return LockCheck(
        name=f"exists.{path.relative_to(ROOT).as_posix()}",
        status="PASS" if ok else "FAIL",
        message="required path exists" if ok else "required path missing",
        path=str(path),
    )


def _contains_all(path: Path, markers: Iterable[str], *, name: str) -> list[LockCheck]:
    text = _read(path)
    checks: list[LockCheck] = []
    for marker in markers:
        checks.append(
            LockCheck(
                name=f"{name}.contains.{marker}",
                status="PASS" if marker in text else "FAIL",
                message=f"marker {'present' if marker in text else 'missing'}: {marker}",
                path=str(path),
            )
        )
    return checks


def _contains_none(path: Path, markers: Iterable[str], *, name: str) -> list[LockCheck]:
    text = _read(path)
    checks: list[LockCheck] = []
    for marker in markers:
        checks.append(
            LockCheck(
                name=f"{name}.absent.{marker}",
                status="PASS" if marker not in text else "FAIL",
                message=f"forbidden marker {'absent' if marker not in text else 'present'}: {marker}",
                path=str(path),
            )
        )
    return checks


def _regex_check(path: Path, pattern: str, *, name: str, should_match: bool = True) -> LockCheck:
    text = _read(path)
    matched = re.search(pattern, text, flags=re.MULTILINE) is not None
    ok = matched if should_match else not matched
    return LockCheck(
        name=name,
        status="PASS" if ok else "FAIL",
        message=(
            f"pattern {'present' if should_match else 'absent'}: {pattern}"
            if ok
            else f"pattern check failed: {pattern}"
        ),
        path=str(path),
    )


def run_lock_checks(root: Path = ROOT) -> dict:
    global ROOT
    ROOT = root.resolve()
    checks: list[LockCheck] = []

    required_paths = [
        ROOT / "main.py",
        ROOT / "run_live.sh",
        ROOT / "runtime_contract.py",
        ROOT / "RUNTIME_SOURCE_MANIFEST.json",
        ROOT / "runtime_native" / "tradebot_main.py",
        ROOT / "scripts" / "operator_boot.py",
        ROOT / "scripts" / "kite_autologin_localhost.py",
        ROOT / "api" / "runtime_ownership.py",
        ROOT / "api" / "auth_visibility.py",
        ROOT / "dashboard" / "runtime_ownership_panel.py",
        ROOT / "dashboard" / "auth_visibility_panel.py",
        ROOT / "docs" / "external-runtime-deprecation.md",
        ROOT / "docs" / "broker-auth-visibility.md",
        ROOT / "docs" / "runtime-ownership-api.md",
        ROOT / "docs" / "operator-boot-commands.md",
        ROOT / "docs" / "native-main-boot.md",
        ROOT / "docs" / "kite-local-login-helper.md",
    ]
    required_dirs = [ROOT / "core", ROOT / "config"]
    checks.extend(_exists(path) for path in required_paths)
    checks.extend(_exists(path, directory=True) for path in required_dirs)

    main_py = ROOT / "main.py"
    checks.extend(
        _contains_none(
            main_py,
            [
                "importlib.util.spec_from_file_location",
                "_load_runtime_main",
                "Algotradify runtime bootstrap failed",
                "runtime_root = resolve_runtime_root()",
            ],
            name="root_main.native_lock",
        )
    )
    checks.extend(
        _contains_all(
            main_py,
            [
                "from core.orchestrator import Orchestrator",
                "from core.auth import validate_kite_startup_credentials",
                "from core.security_guard import enforce_startup_security",
                "from core.instance_lock import InstanceLock",
                "run_readiness_check(write_log=True)",
                "orchestrator.live_monitoring()",
            ],
            name="root_main.safety_markers",
        )
    )

    run_live = ROOT / "run_live.sh"
    checks.extend(
        _contains_all(
            run_live,
            [
                "--start requires --i-understand-live-risk",
                "DRY_RUN=true is incompatible with LIVE startup",
                'export TRADING_MODE="LIVE"',
                'export EXECUTION_MODE="LIVE"',
                'export ALGOTRADIFY_REQUIRE_NATIVE_RUNTIME="true"',
                "scripts/kite_autologin_localhost.py",
            ],
            name="run_live.guarded_live_lock",
        )
    )
    checks.append(
        _regex_check(
            run_live,
            r"selected_count=\$\(\(START \+ VALIDATE_ONLY \+ LOGIN_ONLY\)\)",
            name="run_live.requires_single_action",
        )
    )

    login_helper = ROOT / "scripts" / "kite_autologin_localhost.py"
    checks.extend(
        _contains_all(
            login_helper,
            [
                "KiteConnect",
                "generate_session",
                "kite_access_token",
                "chmod(stat.S_IRUSR | stat.S_IWUSR)",
                "--print-login-url-only",
            ],
            name="kite_login_helper.local_token_flow",
        )
    )
    checks.extend(
        _contains_none(
            login_helper,
            [
                "submit_order",
                "place_order",
                "modify_order",
                "cancel_order",
                "EXECUTION_MODE",
                "TRADING_MODE",
                "print(api_secret",
                "print(access_token",
            ],
            name="kite_login_helper.no_order_or_secret_output",
        )
    )

    operator_boot = ROOT / "scripts" / "operator_boot.py"
    checks.extend(
        _contains_all(
            operator_boot,
            [
                'sub.add_parser("preflight"',
                'sub.add_parser("sim"',
                'sub.add_parser("paper"',
                'sub.add_parser("ui-api"',
                '"EXECUTION_MODE": "SIM"',
                '"EXECUTION_MODE": "PAPER"',
            ],
            name="operator_boot.safe_commands",
        )
    )
    checks.extend(
        _contains_none(
            operator_boot,
            ['"EXECUTION_MODE": "LIVE"', '"TRADING_MODE": "LIVE"'],
            name="operator_boot.no_live_command",
        )
    )

    runtime_contract = ROOT / "runtime_contract.py"
    checks.extend(
        _contains_all(
            runtime_contract,
            [
                "ALLOW_EXTERNAL_ENV = \"ALGOTRADIFY_ALLOW_EXTERNAL_RUNTIME\"",
                "EXTERNAL_RUNTIME_DEPRECATION_MESSAGE",
                "def external_runtime_allowed(*, default: bool = False) -> bool:",
                "return _env_flag(ALLOW_EXTERNAL_ENV, default=default)",
                "def external_runtime_deprecated() -> bool:",
                "external_runtime_fallback.deprecated",
            ],
            name="runtime_contract.external_deprecation_lock",
        )
    )
    checks.extend(
        _contains_all(
            runtime_contract,
            [
                "NATIVE_MANIFEST = \"RUNTIME_SOURCE_MANIFEST.json\"",
                "NATIVE_ENTRYPOINT_SNAPSHOT = \"runtime_native/tradebot_main.py\"",
                "return \"NATIVE\"",
            ],
            name="runtime_contract.native_lock",
        )
    )

    route_files = {
        "api/runtime_ownership_route.py": "/runtime/ownership",
        "api/auth_visibility_route.py": "/broker/auth/visibility",
    }
    for rel, route in route_files.items():
        path = ROOT / rel
        checks.extend(_contains_all(path, [f'@app.get("{route}"'], name=f"{rel}.get_only"))
        checks.extend(_contains_none(path, ["@app.post", "@app.put", "@app.patch", "@app.delete"], name=f"{rel}.no_mutation_routes"))

    for path in [ROOT / "api" / "runtime_ownership.py", ROOT / "api" / "auth_visibility.py"]:
        checks.extend(
            _contains_all(
                path,
                [
                    '"read_only": True',
                    '"is_order_action": False',
                    '"broker_api_called": False',
                    '"real_order_id": None',
                    '"live_mode_touched": False',
                ],
                name=f"{path.relative_to(ROOT).as_posix()}.safe_flags",
            )
        )

    auth_visibility = ROOT / "api" / "auth_visibility.py"
    checks.extend(
        _contains_all(
            auth_visibility,
            [
                '"profile_probe_called": False',
                '"token_mutated": False',
                '"raw_token_exposed": False',
                '"api_secret_exposed": False',
            ],
            name="auth_visibility.no_secret_mutation_lock",
        )
    )

    for path in [ROOT / "dashboard" / "runtime_ownership_panel.py", ROOT / "dashboard" / "auth_visibility_panel.py"]:
        checks.extend(
            _contains_all(
                path,
                [
                    '"read_only_panel": True',
                    '"allowed_actions": []',
                    '"submit_order"',
                    '"toggle_live"',
                ],
                name=f"{path.relative_to(ROOT).as_posix()}.actionless_panel_lock",
            )
        )

    for pr in range(1, 11):
        for role in ("grill", "gsd", "hermes"):
            checks.append(_exists(ROOT / "docs" / "pr-handoffs" / f"RUNTIME-CORRECTION-PR{pr}-{role}.md"))

    forbidden_repo_paths = [
        ROOT / ".env",
        ROOT / ".runtime" / "kite_access_token",
        ROOT / "runtime" / "kite_access_token",
        ROOT / "kite_access_token",
    ]
    for path in forbidden_repo_paths:
        checks.append(
            LockCheck(
                name=f"forbidden_artifact.absent.{path.relative_to(ROOT).as_posix()}",
                status="PASS" if not path.exists() else "FAIL",
                message="forbidden runtime/secret artifact absent" if not path.exists() else "forbidden runtime/secret artifact present",
                path=str(path),
            )
        )

    fail_count = sum(1 for check in checks if check.status == "FAIL")
    payload = {
        "contract": "runtime_migration_lock_v1",
        "status": "PASS" if fail_count == 0 else "FAIL",
        "fail_count": fail_count,
        "pass_count": sum(1 for check in checks if check.status == "PASS"),
        "read_only": True,
        "is_order_action": False,
        "broker_api_called": False,
        "real_order_id": None,
        "live_mode_touched": False,
        "checks": [check.to_dict() for check in checks],
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Runtime Correction migration lock")
    parser.add_argument("--json", action="store_true", help="Print full JSON payload")
    args = parser.parse_args()
    payload = run_lock_checks(ROOT)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"runtime_migration_lock status={payload['status']} pass={payload['pass_count']} fail={payload['fail_count']}")
        for check in payload["checks"]:
            if check["status"] == "FAIL":
                print(f"FAIL {check['name']}: {check['message']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
