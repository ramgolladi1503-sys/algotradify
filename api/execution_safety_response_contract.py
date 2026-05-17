from __future__ import annotations

from typing import Any


EXECUTION_SAFETY_RESPONSE_SCHEMA_VERSION = "1.0"
EXECUTION_SAFETY_RESPONSE_CONTRACT_TYPE = "EXECUTION_SAFETY_RESPONSE_CONTRACT"

EXECUTION_SAFETY_REQUIRED_KEYS = frozenset(
    {
        "execution_permitted",
        "mode",
        "status",
        "blockers",
        "warnings",
        "audit",
        "requires_manual_approval",
        "simulated_order_allowed",
        "paper_order_allowed",
        "broker_api_allowed",
        "real_order_allowed",
        "is_order_action",
        "execution_mode_api_parse",
        "top_executable",
        "readiness_records_checked",
        "safety_visibility_only",
    }
)

EXECUTION_MODE_PARSE_REQUIRED_KEYS = frozenset(
    {
        "mode",
        "raw_mode",
        "invalid_mode",
        "supported_modes",
        "blockers",
        "warnings",
        "is_order_action",
    }
)

EXECUTION_SAFETY_BOOL_KEYS = frozenset(
    {
        "execution_permitted",
        "requires_manual_approval",
        "simulated_order_allowed",
        "paper_order_allowed",
        "broker_api_allowed",
        "real_order_allowed",
        "is_order_action",
        "safety_visibility_only",
    }
)

EXECUTION_SAFETY_LIST_KEYS = frozenset({"blockers", "warnings"})
EXECUTION_SAFETY_SUPPORTED_MODES = ("SIM", "PAPER", "LIVE")
EXECUTION_SAFETY_SAFE_FALSE_FLAGS = frozenset(
    {
        "is_order_action",
        "broker_api_allowed",
        "real_order_allowed",
    }
)


def execution_safety_response_schema_contract() -> dict[str, Any]:
    return {
        "contract_type": EXECUTION_SAFETY_RESPONSE_CONTRACT_TYPE,
        "schema_version": EXECUTION_SAFETY_RESPONSE_SCHEMA_VERSION,
        "required_keys": sorted(EXECUTION_SAFETY_REQUIRED_KEYS),
        "execution_mode_parse_required_keys": sorted(EXECUTION_MODE_PARSE_REQUIRED_KEYS),
        "bool_keys": sorted(EXECUTION_SAFETY_BOOL_KEYS),
        "list_keys": sorted(EXECUTION_SAFETY_LIST_KEYS),
        "supported_modes": list(EXECUTION_SAFETY_SUPPORTED_MODES),
        "safe_false_flags": sorted(EXECUTION_SAFETY_SAFE_FALSE_FLAGS),
        "visibility_only_key": "safety_visibility_only",
    }


def validate_execution_safety_response_contract(payload: dict[str, Any]) -> dict[str, Any]:
    missing_keys = sorted(EXECUTION_SAFETY_REQUIRED_KEYS.difference(payload))
    type_errors: list[str] = []
    safe_flag_violations: list[str] = []

    for key in EXECUTION_SAFETY_BOOL_KEYS.intersection(payload):
        if not isinstance(payload.get(key), bool):
            type_errors.append(f"{key}:expected_bool")

    for key in EXECUTION_SAFETY_LIST_KEYS.intersection(payload):
        if not isinstance(payload.get(key), list):
            type_errors.append(f"{key}:expected_list")

    if payload.get("mode") not in EXECUTION_SAFETY_SUPPORTED_MODES:
        type_errors.append("mode:unsupported")

    if not isinstance(payload.get("audit"), dict):
        type_errors.append("audit:expected_dict")

    if not isinstance(payload.get("top_executable"), dict):
        type_errors.append("top_executable:expected_dict")

    if not isinstance(payload.get("readiness_records_checked"), int):
        type_errors.append("readiness_records_checked:expected_int")

    parse_payload = payload.get("execution_mode_api_parse")
    if not isinstance(parse_payload, dict):
        type_errors.append("execution_mode_api_parse:expected_dict")
        parse_missing_keys = sorted(EXECUTION_MODE_PARSE_REQUIRED_KEYS)
    else:
        parse_missing_keys = sorted(EXECUTION_MODE_PARSE_REQUIRED_KEYS.difference(parse_payload))
        if parse_payload.get("mode") not in EXECUTION_SAFETY_SUPPORTED_MODES:
            type_errors.append("execution_mode_api_parse.mode:unsupported")
        if not isinstance(parse_payload.get("invalid_mode"), bool):
            type_errors.append("execution_mode_api_parse.invalid_mode:expected_bool")
        for key in ("supported_modes", "blockers", "warnings"):
            if not isinstance(parse_payload.get(key), list):
                type_errors.append(f"execution_mode_api_parse.{key}:expected_list")
        if parse_payload.get("is_order_action") is not False:
            safe_flag_violations.append("execution_mode_api_parse.is_order_action must be false")

    for key in EXECUTION_SAFETY_SAFE_FALSE_FLAGS:
        if payload.get(key) is not False:
            safe_flag_violations.append(f"{key} must be false")

    valid = not missing_keys and not parse_missing_keys and not type_errors and not safe_flag_violations
    return {
        "contract_type": EXECUTION_SAFETY_RESPONSE_CONTRACT_TYPE,
        "schema_version": EXECUTION_SAFETY_RESPONSE_SCHEMA_VERSION,
        "valid": valid,
        "missing_keys": missing_keys,
        "execution_mode_parse_missing_keys": parse_missing_keys,
        "type_errors": type_errors,
        "safe_flag_violations": safe_flag_violations,
    }
