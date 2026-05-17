from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from movement_engine.context import StrategyContext
from movement_engine.contract import StrategyCandidate


ProviderCandidate = StrategyCandidate | Mapping[str, Any]
ProviderOutput = ProviderCandidate | Iterable[ProviderCandidate] | None
MovementStrategyProvider = Callable[[StrategyContext], ProviderOutput]


@dataclass(frozen=True)
class MovementProviderRegistrationResult:
    valid: bool
    strategy_id: str | None = None
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "strategy_id": self.strategy_id,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "is_order_action": self.is_order_action,
        }


@dataclass(frozen=True)
class MovementRegistryRunResult:
    candidates: tuple[ProviderCandidate, ...] = ()
    warnings: tuple[str, ...] = ()
    diagnostics: tuple[dict[str, Any], ...] = ()
    provider_count: int = 0

    @property
    def is_order_action(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidates": [_candidate_to_dict(candidate) for candidate in self.candidates],
            "warnings": list(self.warnings),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "provider_count": self.provider_count,
            "candidate_count": len(self.candidates),
            "is_order_action": self.is_order_action,
        }


class MovementStrategyRegistry:
    """Read-only shell for movement strategy providers.

    Providers are pure candidate producers. They must not place orders, call
    brokers, mutate runtime state, or hide exceptions from the registry.
    """

    def __init__(self) -> None:
        self._providers: dict[str, MovementStrategyProvider] = {}

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    @property
    def strategy_ids(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

    def register_provider(
        self,
        strategy_id: str,
        provider: MovementStrategyProvider,
    ) -> MovementProviderRegistrationResult:
        normalized_strategy_id = str(strategy_id or "").strip()
        blockers: list[str] = []

        if not normalized_strategy_id:
            blockers.append("STRATEGY_ID_REQUIRED")
        if not callable(provider):
            blockers.append("PROVIDER_MUST_BE_CALLABLE")
        if normalized_strategy_id and normalized_strategy_id in self._providers:
            blockers.append("DUPLICATE_STRATEGY_PROVIDER")

        if blockers:
            return MovementProviderRegistrationResult(
                valid=False,
                strategy_id=normalized_strategy_id or None,
                blockers=tuple(_dedupe(blockers)),
            )

        self._providers[normalized_strategy_id] = provider
        return MovementProviderRegistrationResult(valid=True, strategy_id=normalized_strategy_id)

    def run(self, context: StrategyContext) -> MovementRegistryRunResult:
        candidates: list[ProviderCandidate] = []
        warnings: list[str] = []
        diagnostics: list[dict[str, Any]] = []

        if context is None:
            return MovementRegistryRunResult(
                candidates=(),
                warnings=("CONTEXT_REQUIRED",),
                diagnostics=(
                    _diagnostic(
                        code="CONTEXT_REQUIRED",
                        strategy_id=None,
                        message="StrategyContext is required to run movement providers.",
                    ),
                ),
                provider_count=len(self._providers),
            )

        for strategy_id, provider in self._providers.items():
            try:
                output = provider(context)
                provider_items = _normalize_provider_output(output)
            except Exception as exc:  # defensive shell boundary; provider bugs must not crash the engine.
                warning = f"PROVIDER_EXCEPTION:{strategy_id}"
                warnings.append(warning)
                diagnostics.append(
                    _diagnostic(
                        code="PROVIDER_EXCEPTION",
                        strategy_id=strategy_id,
                        message=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )
                continue

            for item_index, item in enumerate(provider_items):
                if isinstance(item, StrategyCandidate):
                    candidates.append(item)
                elif isinstance(item, Mapping):
                    candidates.append(dict(item))
                else:
                    warning = f"INVALID_PROVIDER_OUTPUT:{strategy_id}"
                    warnings.append(warning)
                    diagnostics.append(
                        _diagnostic(
                            code="INVALID_PROVIDER_OUTPUT",
                            strategy_id=strategy_id,
                            message="Provider returned an item that is not a StrategyCandidate or mapping.",
                            item_index=item_index,
                            item_type=type(item).__name__,
                        )
                    )

        return MovementRegistryRunResult(
            candidates=tuple(candidates),
            warnings=tuple(_dedupe(warnings)),
            diagnostics=tuple(diagnostics),
            provider_count=len(self._providers),
        )


def _normalize_provider_output(output: ProviderOutput) -> list[Any]:
    if output is None:
        return []
    if isinstance(output, (StrategyCandidate, Mapping)):
        return [output]
    if isinstance(output, (str, bytes)):
        return [output]
    if isinstance(output, Iterable):
        return list(output)
    return [output]


def _candidate_to_dict(candidate: ProviderCandidate) -> dict[str, Any]:
    if isinstance(candidate, StrategyCandidate):
        return candidate.to_dict()
    return dict(candidate)


def _diagnostic(
    *,
    code: str,
    strategy_id: str | None,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "strategy_id": strategy_id,
        "message": message,
        "is_order_action": False,
    }
    payload.update(extra)
    return payload


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
