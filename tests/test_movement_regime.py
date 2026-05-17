from __future__ import annotations

from movement_engine import MovementRegime, StrategyContext, classify_movement_regime


def test_regime_classifier_returns_inconclusive_without_context():
    result = classify_movement_regime(None)

    assert result.primary_regime == MovementRegime.INCONCLUSIVE
    assert result.scores["INCONCLUSIVE"] == 1.0
    assert "CONTEXT_REQUIRED" in result.warnings
    assert result.is_order_action is False


def test_regime_classifier_returns_inconclusive_when_spot_or_vwap_missing():
    result = classify_movement_regime(StrategyContext(symbol="NIFTY", ts_epoch=1.0, spot_ltp=None, vwap=100.0))

    assert result.primary_regime == MovementRegime.INCONCLUSIVE
    assert "SPOT_LTP_MISSING" in result.warnings
    assert "INSUFFICIENT_REGIME_EVIDENCE" in result.warnings
    assert result.to_dict()["is_order_action"] is False


def test_regime_classifier_detects_trend_up():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=102.0,
        vwap=100.0,
        day_low=99.0,
        day_high=102.5,
        ce_premium_change=18.0,
        pe_premium_change=-6.0,
        range_width_pct=0.8,
        volume_z=1.0,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.TREND_UP
    assert result.scores["TREND_UP"] > result.scores["TREND_DOWN"]
    assert result.scores["TREND_UP"] > 0.3


def test_regime_classifier_detects_trend_down():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=98.0,
        vwap=100.0,
        day_low=97.5,
        day_high=101.0,
        ce_premium_change=-8.0,
        pe_premium_change=20.0,
        range_width_pct=0.8,
        volume_z=1.0,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.TREND_DOWN
    assert result.scores["TREND_DOWN"] > result.scores["TREND_UP"]
    assert result.scores["TREND_DOWN"] > 0.3


def test_regime_classifier_detects_range_near_midpoint():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=100.1,
        vwap=100.0,
        day_low=98.0,
        day_high=102.0,
        ce_premium_change=2.0,
        pe_premium_change=1.0,
        range_width_pct=0.7,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.RANGE
    assert result.scores["RANGE"] >= 0.35


def test_regime_classifier_detects_chop():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=100.02,
        vwap=100.0,
        day_low=99.8,
        day_high=100.2,
        ce_premium_change=1.0,
        pe_premium_change=-1.0,
        range_width_pct=0.25,
        volume_z=-0.8,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.CHOP
    assert result.scores["CHOP"] >= 0.55


def test_regime_classifier_detects_compression():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=100.2,
        vwap=100.0,
        day_low=99.7,
        day_high=100.5,
        atr_short=0.5,
        atr_long=1.0,
        range_width_pct=0.30,
        ce_premium_change=4.0,
        pe_premium_change=1.0,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.COMPRESSION
    assert result.scores["COMPRESSION"] >= 0.7
    assert result.evidence["atr_ratio"] == 0.5


def test_regime_classifier_detects_volatility_expansion():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=101.2,
        vwap=100.0,
        day_low=99.0,
        day_high=102.0,
        atr=1.5,
        atr_short=1.8,
        atr_long=1.0,
        range_width_pct=1.2,
        volume_z=2.0,
        ce_premium_change=10.0,
        pe_premium_change=-4.0,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.VOLATILITY_EXPANSION
    assert result.scores["VOLATILITY_EXPANSION"] >= 0.65


def test_regime_classifier_detects_trap_risk():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=101.9,
        vwap=100.0,
        day_low=98.0,
        day_high=102.0,
        ce_premium_change=-2.0,
        pe_premium_change=8.0,
        range_width_pct=0.9,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.TRAP_RISK
    assert result.scores["TRAP_RISK"] >= 0.55


def test_regime_classifier_detects_exhaustion_risk():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=103.0,
        vwap=100.0,
        day_low=99.0,
        day_high=103.2,
        ce_premium_change=-3.0,
        pe_premium_change=2.0,
        range_width_pct=1.0,
    )

    result = classify_movement_regime(context)

    assert result.primary_regime == MovementRegime.EXHAUSTION_RISK
    assert result.scores["EXHAUSTION_RISK"] >= 0.5


def test_regime_hint_can_break_ties_but_not_create_order_action():
    context = StrategyContext(
        symbol="NIFTY",
        ts_epoch=1.0,
        spot_ltp=100.1,
        vwap=100.0,
        day_low=98.0,
        day_high=102.0,
        regime_hint="COMPRESSION",
    )

    result = classify_movement_regime(context)

    assert result.scores["COMPRESSION"] >= 0.15
    assert result.is_order_action is False
