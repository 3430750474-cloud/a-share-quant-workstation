"""Core smoke tests for market generation, strategy signals and backtests."""

import pytest

from strategies import (
    STRATEGY_ORDER,
    classify_quality,
    classify_strength,
    screen_market,
)
from backtest import run_backtest
from market import MarketEngine


@pytest.fixture(scope="module")
def engine():
    return MarketEngine(history_days=300)


def test_market_generation_and_minute_replay(engine):
    assert len(engine.universe) >= 300
    assert len(engine.bars["600519"]) == 300
    snapshot = engine.minute_snapshot("600519", "5m", limit=60)
    assert len(snapshot["bars"]) == 60
    assert snapshot["bars"][0]["open"] > 0


def test_signal_labels_and_quality_vocabulary(engine):
    signals = screen_market(engine)
    assert isinstance(signals, list)
    if signals:
        for signal in signals:
            assert signal["strength"] in ("强", "中", "弱")
            assert signal["quality"] in ("高", "合格", "差")
            assert 0 <= signal["score"] <= 100
    assert classify_strength(90) == "强"
    assert classify_strength(65) == "中"
    assert classify_strength(40) == "弱"
    assert classify_quality(90, 2.5) == "高"
    assert classify_quality(70, 1.5) == "合格"
    assert classify_quality(40, 1.0) == "差"


def test_every_strategy_has_independent_backtest_report(engine):
    reports = {}
    for strategy_id in STRATEGY_ORDER:
        report = run_backtest(engine, strategy_id, 1_000_000)
        reports[strategy_id] = report
        assert report["strategy_id"] == strategy_id
        assert "win_rate" in report
        assert 0 <= report["win_rate"] <= 100
        assert "metrics" in report
        assert "equity_curve" in report
    assert set(reports) == set(STRATEGY_ORDER)
