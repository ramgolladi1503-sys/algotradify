from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.dry_run_execution_route import (
    DRY_RUN_EXPORT_BUNDLE_TYPE,
    DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS,
    DRY_RUN_EXPORT_REQUIRED_KEYS,
    DRY_RUN_EXPORT_SAFE_FLAGS,
    DRY_RUN_EXPORT_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class EvidenceSchema:
    schema_id: str
    evidence_type: str
    schema_version: str
    compatible_schema_versions: tuple[str, ...]
    required_keys: frozenset[str]
    safe_flags: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_contract(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "evidence_type": self.evidence_type,
            "schema_version": self.schema_version,
            "compatible_schema_versions": list(self.compatible_schema_versions),
            "required_keys": sorted(self.required_keys),
            "safe_flags": dict(self.safe_flags),
            "description": self.description,
        }


SCHEMA_VERSION_1 = "1.0"

DRY_RUN_EXECUTION_PAYLOAD_KEYS = frozenset(
    {
        "created",
        "candidate_id",
        "dry_run_only",
        "is_order_action",
        "broker_api_called",
        "real_order_id",
        "intent",
        "lifecycle_event",
        "outcome_event",
        "blockers",
        "warnings",
    }
)

EXECUTION_SAFETY_DECISION_KEYS = frozenset(
    {
        "execution_permitted",
        "status",
        "is_order_action",
        "safety_visibility_only",
        "blockers",
        "warnings",
    }
)

APPROVAL_EVIDENCE_KEYS = frozenset(
    {
        "candidate_id",
        "current_status",
        "approval_id",
        "operator_id",
        "events",
        "blockers",
        "is_order_action",
    }
)

READINESS_SNAPSHOT_KEYS = frozenset(
    {
        "candidate_id",
        "execution_allowed",
    }
)

LIFECYCLE_EVENT_KEYS = frozenset(
    {
        "status",
        "dry_run_only",
        "broker_api_called",
        "real_order_id",
    }
)

OUTCOME_REPLAY_EVENT_KEYS = frozenset(
    {
        "status",
        "evidence",
        "real_order_id",
    }
)

EVIDENCE_SCHEMA_REGISTRY: dict[str, EvidenceSchema] = {
    "dry_run_export_bundle": EvidenceSchema(
        schema_id="dry_run_export_bundle",
        evidence_type=DRY_RUN_EXPORT_BUNDLE_TYPE,
        schema_version=DRY_RUN_EXPORT_SCHEMA_VERSION,
        compatible_schema_versions=DRY_RUN_EXPORT_COMPATIBLE_SCHEMA_VERSIONS,
        required_keys=DRY_RUN_EXPORT_REQUIRED_KEYS,
        safe_flags=DRY_RUN_EXPORT_SAFE_FLAGS,
        description="Read-only dry-run evidence export bundle consumed by Control Tower export preview.",
    ),
    "dry_run_execution_payload": EvidenceSchema(
        schema_id="dry_run_execution_payload",
        evidence_type="DRY_RUN_EXECUTION_PAYLOAD",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=DRY_RUN_EXECUTION_PAYLOAD_KEYS,
        safe_flags={
            "dry_run_only": True,
            "is_order_action": False,
            "broker_api_called": False,
            "real_order_id": None,
        },
        description="Dry-run adapter response before export bundle wrapping.",
    ),
    "execution_safety_decision": EvidenceSchema(
        schema_id="execution_safety_decision",
        evidence_type="EXECUTION_SAFETY_DECISION",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=EXECUTION_SAFETY_DECISION_KEYS,
        safe_flags={"is_order_action": False, "safety_visibility_only": True},
        description="Execution safety gate decision used before dry-run intent creation.",
    ),
    "approval_evidence": EvidenceSchema(
        schema_id="approval_evidence",
        evidence_type="APPROVAL_EVIDENCE",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=APPROVAL_EVIDENCE_KEYS,
        safe_flags={"is_order_action": False},
        description="Operator approval evidence consumed by the dry-run adapter.",
    ),
    "readiness_snapshot": EvidenceSchema(
        schema_id="readiness_snapshot",
        evidence_type="READINESS_SNAPSHOT",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=READINESS_SNAPSHOT_KEYS,
        safe_flags={},
        description="Matched execution-readiness snapshot for the selected candidate.",
    ),
    "lifecycle_event": EvidenceSchema(
        schema_id="lifecycle_event",
        evidence_type="DRY_RUN_LIFECYCLE_EVENT",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=LIFECYCLE_EVENT_KEYS,
        safe_flags={"dry_run_only": True, "broker_api_called": False, "real_order_id": None},
        description="Dry-run lifecycle evidence event emitted after intent creation.",
    ),
    "outcome_replay_event": EvidenceSchema(
        schema_id="outcome_replay_event",
        evidence_type="OUTCOME_REPLAY_EVENT",
        schema_version=SCHEMA_VERSION_1,
        compatible_schema_versions=(SCHEMA_VERSION_1,),
        required_keys=OUTCOME_REPLAY_EVENT_KEYS,
        safe_flags={"real_order_id": None},
        description="Outcome replay event used by replay drilldowns and analytics.",
    ),
}


def list_evidence_schema_ids() -> list[str]:
    return sorted(EVIDENCE_SCHEMA_REGISTRY)


def get_evidence_schema(schema_id: str) -> EvidenceSchema:
    try:
        return EVIDENCE_SCHEMA_REGISTRY[schema_id]
    except KeyError as exc:
        raise KeyError(f"unknown evidence schema: {schema_id}") from exc


def evidence_schema_registry_snapshot() -> dict[str, dict[str, Any]]:
    return {schema_id: EVIDENCE_SCHEMA_REGISTRY[schema_id].to_contract() for schema_id in list_evidence_schema_ids()}
