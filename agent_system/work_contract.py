from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any


AGENT_WORK_SCHEMA_VERSION = 1


class AgentSource(str, Enum):
    """Known sources allowed to submit agent work requests."""

    GSD = "gsd"
    HERMES = "hermes"
    GRILL_ME = "grill_me"
    MANUAL = "manual"


class AgentAction(str, Enum):
    """Agent action vocabulary.

    The enum intentionally contains safe and forbidden actions. Forbidden actions must stay
    representable so later guards can reject them with structured reasons instead of treating
    them as unknown text.
    """

    CRITIQUE_SCOPE = "CRITIQUE_SCOPE"
    REVIEW_PR = "REVIEW_PR"
    AUDIT_RISK = "AUDIT_RISK"
    FIND_FAKE_PROGRESS = "FIND_FAKE_PROGRESS"

    DESIGN_ARCHITECTURE = "DESIGN_ARCHITECTURE"
    DEFINE_CONTRACT = "DEFINE_CONTRACT"
    MAP_WORKFLOW = "MAP_WORKFLOW"
    CREATE_ACCEPTANCE_GATES = "CREATE_ACCEPTANCE_GATES"

    PLAN_PR = "PLAN_PR"
    GENERATE_TESTS = "GENERATE_TESTS"
    GENERATE_PATCH = "GENERATE_PATCH"
    FIX_TEST_FAILURE = "FIX_TEST_FAILURE"
    UPDATE_DOCS = "UPDATE_DOCS"

    PLACE_ORDER = "PLACE_ORDER"
    MODIFY_ORDER = "MODIFY_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    EXIT_POSITION = "EXIT_POSITION"
    ENABLE_LIVE = "ENABLE_LIVE"
    DISABLE_RISK_GATE = "DISABLE_RISK_GATE"
    CHANGE_BROKER_CONFIG = "CHANGE_BROKER_CONFIG"
    CHANGE_LIVE_CONFIG = "CHANGE_LIVE_CONFIG"
    CALL_BROKER_API = "CALL_BROKER_API"


class AgentRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKED = "BLOCKED"


SAFE_AGENT_ACTIONS = frozenset(
    {
        AgentAction.CRITIQUE_SCOPE.value,
        AgentAction.REVIEW_PR.value,
        AgentAction.AUDIT_RISK.value,
        AgentAction.FIND_FAKE_PROGRESS.value,
        AgentAction.DESIGN_ARCHITECTURE.value,
        AgentAction.DEFINE_CONTRACT.value,
        AgentAction.MAP_WORKFLOW.value,
        AgentAction.CREATE_ACCEPTANCE_GATES.value,
        AgentAction.PLAN_PR.value,
        AgentAction.GENERATE_TESTS.value,
        AgentAction.GENERATE_PATCH.value,
        AgentAction.FIX_TEST_FAILURE.value,
        AgentAction.UPDATE_DOCS.value,
    }
)

FORBIDDEN_AGENT_ACTIONS = frozenset(
    {
        AgentAction.PLACE_ORDER.value,
        AgentAction.MODIFY_ORDER.value,
        AgentAction.CANCEL_ORDER.value,
        AgentAction.EXIT_POSITION.value,
        AgentAction.ENABLE_LIVE.value,
        AgentAction.DISABLE_RISK_GATE.value,
        AgentAction.CHANGE_BROKER_CONFIG.value,
        AgentAction.CHANGE_LIVE_CONFIG.value,
        AgentAction.CALL_BROKER_API.value,
    }
)


class AgentWorkValidationError(ValueError):
    """Raised when an agent work request payload is structurally invalid."""


def _require_mapping(payload: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise AgentWorkValidationError("AGENT_WORK_PAYLOAD_MUST_BE_OBJECT")
    return payload


def _required_clean_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AgentWorkValidationError(f"{key.upper()}_MUST_BE_STRING")
    cleaned = value.strip()
    if not cleaned:
        raise AgentWorkValidationError(f"{key.upper()}_MISSING")
    return cleaned


def _string_tuple(payload: Mapping[str, Any], key: str, *, required: bool = False) -> tuple[str, ...]:
    value = payload.get(key, [])
    if value is None:
        value = []
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise AgentWorkValidationError(f"{key.upper()}_MUST_BE_LIST")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise AgentWorkValidationError(f"{key.upper()}_ITEM_MUST_BE_STRING")
        cleaned = item.strip().replace("\\", "/")
        if cleaned:
            normalized.append(cleaned)

    if required and not normalized:
        raise AgentWorkValidationError(f"{key.upper()}_MISSING")

    return tuple(normalized)


def _metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = payload.get("metadata", {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise AgentWorkValidationError("METADATA_MUST_BE_OBJECT")
    return dict(value)


def _schema_version(payload: Mapping[str, Any]) -> int:
    value = payload.get("schema_version", AGENT_WORK_SCHEMA_VERSION)
    if not isinstance(value, int):
        raise AgentWorkValidationError("SCHEMA_VERSION_MUST_BE_INTEGER")
    if value != AGENT_WORK_SCHEMA_VERSION:
        raise AgentWorkValidationError("SCHEMA_VERSION_UNSUPPORTED")
    return value


def _normalize_source(value: str) -> str:
    cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "grill": AgentSource.GRILL_ME.value,
        "grillme": AgentSource.GRILL_ME.value,
        "grill_me": AgentSource.GRILL_ME.value,
        "gsd": AgentSource.GSD.value,
        "hermes": AgentSource.HERMES.value,
        "manual": AgentSource.MANUAL.value,
    }
    normalized = aliases.get(cleaned, cleaned)
    allowed = {source.value for source in AgentSource}
    if normalized not in allowed:
        raise AgentWorkValidationError("SOURCE_AGENT_UNKNOWN")
    return normalized


def _normalize_action(value: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    allowed = {action.value for action in AgentAction}
    if normalized not in allowed:
        raise AgentWorkValidationError("ACTION_UNKNOWN")
    return normalized


@dataclass(frozen=True)
class AgentWorkRequest:
    schema_version: int
    source_agent: str
    action: str
    title: str
    scope: str
    allowed_paths: tuple[str, ...]
    requested_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    requires_human_approval: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_paths"] = list(self.allowed_paths)
        payload["requested_paths"] = list(self.requested_paths)
        payload["forbidden_paths"] = list(self.forbidden_paths)
        payload["metadata"] = dict(self.metadata)
        return payload


def normalize_agent_work_request(payload: Mapping[str, Any] | Any) -> AgentWorkRequest:
    """Normalize and validate an agent work request payload.

    This function validates shape only. It does not approve work. Dangerous but known
    actions, such as PLACE_ORDER, are normalized so Agent PR 2 can block them with
    structured scope-guard reasons.
    """

    raw = _require_mapping(payload)
    schema_version = _schema_version(raw)
    source_agent = _normalize_source(_required_clean_string(raw, "source_agent"))
    action = _normalize_action(_required_clean_string(raw, "action"))
    title = _required_clean_string(raw, "title")
    scope = _required_clean_string(raw, "scope")
    allowed_paths = _string_tuple(raw, "allowed_paths")
    requested_paths = _string_tuple(raw, "requested_paths", required=True)
    forbidden_paths = _string_tuple(raw, "forbidden_paths")
    requires_human_approval = bool(raw.get("requires_human_approval", True))

    return AgentWorkRequest(
        schema_version=schema_version,
        source_agent=source_agent,
        action=action,
        title=title,
        scope=scope,
        allowed_paths=allowed_paths,
        requested_paths=requested_paths,
        forbidden_paths=forbidden_paths,
        requires_human_approval=requires_human_approval,
        metadata=_metadata(raw),
    )


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_agent_work_id(request: AgentWorkRequest) -> str:
    """Build a deterministic work ID from the stable identity fields."""

    identity = {
        "schema_version": request.schema_version,
        "source_agent": request.source_agent,
        "action": request.action,
        "title": request.title,
        "scope": request.scope,
        "requested_paths": list(request.requested_paths),
    }
    return hashlib.sha256(_stable_json(identity).encode("utf-8")).hexdigest()[:24]


def agent_work_schema_contract() -> dict[str, Any]:
    """Return the public contract for Agent PR 1 without importing runtime layers."""

    return {
        "schema_version": AGENT_WORK_SCHEMA_VERSION,
        "contract": "agent_work_request_v1",
        "sources": sorted(source.value for source in AgentSource),
        "safe_actions": sorted(SAFE_AGENT_ACTIONS),
        "forbidden_actions": sorted(FORBIDDEN_AGENT_ACTIONS),
        "required_fields": [
            "schema_version",
            "source_agent",
            "action",
            "title",
            "scope",
            "requested_paths",
        ],
        "path_fields": ["allowed_paths", "requested_paths", "forbidden_paths"],
        "safe_defaults": {
            "read_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "live_mode_touched": False,
            "allowed_for_live_execution": False,
            "real_order_id": None,
        },
        "scope": "contract_only_no_api_no_ui_no_broker_no_live_no_paper_orders",
    }
