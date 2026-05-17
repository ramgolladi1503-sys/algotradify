from __future__ import annotations

from movement_engine import (
    CandidateStatus,
    Direction,
    MovementStrategyRegistry,
    StrategyCandidate,
    StrategyContext,
)


def _context() -> StrategyContext:
    return StrategyContext(symbol="NIFTY", ts_epoch=123.0, spot_ltp=100.0, vwap=99.8)


def _candidate(candidate_id: str = "move-1", strategy_id: str = "TEST_PROVIDER") -> StrategyCandidate:
    return StrategyCandidate(
        schema_version=1,
        candidate_id=candidate_id,
        strategy_id=strategy_id,
        movement_type="TEST_MOVEMENT",
        symbol="NIFTY",
        direction=Direction.BUY_CALL,
        status=CandidateStatus.RAW_CANDIDATE,
        raw_score=0.65,
        confidence_score=0.60,
        price_structure_score=0.60,
        option_confirmation_score=0.50,
        liquidity_score=0.80,
        freshness_score=0.90,
        volatility_score=0.50,
        regime_alignment_score=0.60,
        entry_trigger="test trigger",
        invalid_if="test invalidation",
        rank_reason="test reason",
        evidence={"source": strategy_id},
    )


def test_empty_registry_returns_empty_candidate_list_safely():
    registry = MovementStrategyRegistry()

    result = registry.run(_context())

    assert result.candidates == ()
    assert result.provider_count == 0
    assert result.warnings == ()
    assert result.diagnostics == ()
    assert result.is_order_action is False
    assert result.to_dict()["is_order_action"] is False


def test_single_provider_returns_candidates():
    registry = MovementStrategyRegistry()
    registration = registry.register_provider("TEST_PROVIDER", lambda context: [_candidate()])

    result = registry.run(_context())

    assert registration.valid is True
    assert registry.provider_count == 1
    assert len(result.candidates) == 1
    assert result.candidates[0].candidate_id == "move-1"
    assert result.candidates[0].is_order_action is False


def test_multiple_providers_return_combined_candidates_in_registration_order():
    registry = MovementStrategyRegistry()
    registry.register_provider("A", lambda context: _candidate("move-a", "A"))
    registry.register_provider("B", lambda context: [_candidate("move-b", "B")])

    result = registry.run(_context())

    assert [candidate.candidate_id for candidate in result.candidates] == ["move-a", "move-b"]
    assert result.provider_count == 2


def test_provider_exception_is_diagnostic_not_crash():
    registry = MovementStrategyRegistry()

    def broken_provider(context):
        raise RuntimeError("broken movement logic")

    registry.register_provider("BROKEN", broken_provider)

    result = registry.run(_context())

    assert result.candidates == ()
    assert "PROVIDER_EXCEPTION:BROKEN" in result.warnings
    assert result.diagnostics[0]["code"] == "PROVIDER_EXCEPTION"
    assert result.diagnostics[0]["strategy_id"] == "BROKEN"
    assert result.diagnostics[0]["is_order_action"] is False


def test_invalid_provider_output_is_diagnosed():
    registry = MovementStrategyRegistry()
    registry.register_provider("BAD_OUTPUT", lambda context: ["not-a-candidate"])

    result = registry.run(_context())

    assert result.candidates == ()
    assert "INVALID_PROVIDER_OUTPUT:BAD_OUTPUT" in result.warnings
    assert result.diagnostics[0]["code"] == "INVALID_PROVIDER_OUTPUT"
    assert result.diagnostics[0]["item_type"] == "str"


def test_invalid_registration_is_blocked_without_registering_provider():
    registry = MovementStrategyRegistry()

    result = registry.register_provider("", object())

    assert result.valid is False
    assert "STRATEGY_ID_REQUIRED" in result.blockers
    assert "PROVIDER_MUST_BE_CALLABLE" in result.blockers
    assert registry.provider_count == 0
    assert result.is_order_action is False


def test_duplicate_strategy_registration_is_blocked():
    registry = MovementStrategyRegistry()
    registry.register_provider("DUPLICATE", lambda context: [])
    result = registry.register_provider("DUPLICATE", lambda context: [])

    assert result.valid is False
    assert "DUPLICATE_STRATEGY_PROVIDER" in result.blockers
    assert registry.provider_count == 1


def test_none_context_does_not_crash_registry():
    registry = MovementStrategyRegistry()
    registry.register_provider("TEST_PROVIDER", lambda context: [_candidate()])

    result = registry.run(None)

    assert result.candidates == ()
    assert "CONTEXT_REQUIRED" in result.warnings
    assert result.diagnostics[0]["code"] == "CONTEXT_REQUIRED"
    assert result.is_order_action is False
