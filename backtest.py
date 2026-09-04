"""Daily-bar approximation backtester for the five strategies."""

from __future__ import annotations

import math
from datetime import datetime

from indicators import sma
from strategies import STRATEGIES, STRATEGY_ORDER


COSTS = {
    "commission": 0.00025,
    "stamp_duty": 0.0005,
    "slippage": 0.001,
}


def _exit_trade(bars, entry_idx, entry_price, take, stop, max_hold):
    """Return (exit_date, exit_price, holding_days)."""
    if entry_idx + 1 >= len(bars):
        return None
    start = entry_idx + 1
    end = min(len(bars) - 1, start + max_hold)
    for day in range(start, end + 1):
        bar = bars[day]
        if bar["high"] >= take:
            return bar["date"], take, day - entry_idx
        if bar["low"] <= stop:
            return bar["date"], stop, day - entry_idx
        if day == end:
            return bar["date"], bar["close"], day - entry_idx
    return None


def _signal_for_strategy(strategy_id, bars, opens, highs, lows, closes, volumes, ma5, ma10, ma20):
    n = len(bars)
    if strategy_id == "s1":
        for i in range(2, n):
            prev = bars[i - 1]
            prev_prev = bars[i - 2]
            open_gap = opens[i] / closes[i - 1] - 1
            red = prev["close"] < prev["open"]
            above_ma10 = prev["close"] >= ma10[i - 1] if ma10[i - 1] else False
            shrink = prev_prev["volume"] > prev["volume"]
            if (
                red
                and above_ma10
                and shrink
                and 0.018 <= open_gap <= 0.058
                and not closes[i] >= opens[i] * 1.04
            ):
                entry = opens[i] * (1 + COSTS["slippage"])
                params = STRATEGIES["s1"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    entry * (1 - params["stop_loss"]), params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s2":
        for i in range(8, n):
            prev = bars[i - 1]
            prev_ma5 = ma5[i - 1]
            aligned = all(x is not None for x in (ma5[i - 1], ma10[i - 1], ma20[i - 1]))
            if aligned and ma5[i - 1] >= ma10[i - 1] >= ma20[i - 1]:
                gain5 = closes[i - 1] / closes[i - 6] - 1
                touched = lows[i] <= prev_ma5 * 1.008
                recovered = closes[i] > prev_ma5
                if (
                    prev["close"] >= prev_ma5
                    and 0.06 <= gain5 <= 0.25
                    and touched
                    and recovered
                    and opens[i] / closes[i - 1] - 1 <= 0.04
                ):
                    entry = max(opens[i], prev_ma5 * 1.002) * (1 + COSTS["slippage"])
                    params = STRATEGIES["s2"]["params"]
                    exit_result = _exit_trade(
                        bars, i, entry, entry * (1 + params["take_profit"]),
                        entry * (1 - params["stop_loss"]), params["max_hold"],
                    )
                    if exit_result:
                        yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s3":
        for i in range(23, n):
            window = bars[i - 21 : i - 1]
            high20 = max(b["high"] for b in window)
            low20 = min(b["low"] for b in window)
            width = (high20 - low20) / low20 if low20 else 1
            vol_mean = sum(b["volume"] for b in window) / len(window)
            broken = highs[i] >= high20 * 1.005
            volume_burst = volumes[i] >= vol_mean * 1.8
            room = opens[i] / closes[i - 1] - 1 < 0.05
            if width <= 0.18 and broken and volume_burst and room:
                entry = max(opens[i], high20 * 1.004) * (1 + COSTS["slippage"])
                params = STRATEGIES["s3"]["params"]
                stop = high20 * 0.985
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]), stop,
                    params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s4":
        volume_ma5 = sma(volumes, 5)
        for i in range(8, n):
            prev = closes[i - 1]
            pct = closes[i] / prev - 1
            bar = bars[i]
            near_high = (bar["high"] - closes[i]) <= (bar["high"] - bar["low"]) * 0.35
            vol5 = volume_ma5[i - 1] or 1
            if (
                0.03 <= pct <= 0.075
                and near_high
                and volumes[i] >= vol5 * 1.15
                and opens[i] / prev - 1 <= 0.05
            ):
                entry = closes[i] * (1 + COSTS["slippage"])
                params = STRATEGIES["s4"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    entry * (1 - params["stop_loss"]), params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s5":
        for i in range(8, n):
            prev = bars[i - 1]
            prev_prev = bars[i - 2]
            gain5_prev = closes[i - 2] / closes[i - 7] - 1
            shrink = prev["volume"] < prev_prev["volume"] * 0.8
            reversal = opens[i] < closes[i - 1] < closes[i]
            if (
                gain5_prev >= 0.15
                and -0.07 <= prev["pct"] / 100 <= -0.02
                and shrink
                and reversal
                and closes[i] / closes[i - 1] - 1 <= 0.07
            ):
                entry = closes[i] * (1 + COSTS["slippage"])
                params = STRATEGIES["s5"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    entry * (1 - params["stop_loss"]), params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s6":
        ma60 = sma(closes, 60)
        for i in range(72, n):
            prev = bars[i - 1]
            ma10_i = ma10[i]
            ma20_i = ma20[i]
            ma60_i = ma60[i]
            if not (ma10_i and ma20_i and ma60_i):
                continue
            trend_up = ma20[i - 1] > ma60[i - 1] and ma20[i - 1] > ma20[i - 6]
            pulled = lows[i] <= ma10_i * 1.006
            recovered = closes[i] > ma10_i
            above_slow = closes[i] > ma20_i
            room = opens[i] / closes[i - 1] - 1 <= 0.03
            if (
                trend_up
                and prev["close"] >= ma10[i - 1]
                and pulled
                and recovered
                and above_slow
                and room
            ):
                entry = max(opens[i], ma10_i * 1.002) * (1 + COSTS["slippage"])
                params = STRATEGIES["s6"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    entry * (1 - params["stop_loss"]), params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s7":
        for i in range(24, n):
            window = bars[i - 11 : i - 1]
            high10 = max(b["high"] for b in window)
            low10 = min(b["low"] for b in window)
            width10 = (high10 - low10) / low10 if low10 else 1
            vol10 = sum(b["volume"] for b in window) / len(window)
            values = [x for x in (ma5[i - 1], ma10[i - 1], ma20[i - 1]) if x]
            spread = (max(values) - min(values)) / min(values) if len(values) == 3 and min(values) else 99
            if (
                spread <= 0.05
                and width10 <= 0.12
                and highs[i] >= high10 * 1.003
                and volumes[i] >= vol10 * 1.8
                and closes[i] > opens[i]
            ):
                entry = max(opens[i], high10 * 1.002) * (1 + COSTS["slippage"])
                params = STRATEGIES["s7"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    high10 * 0.975, params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result
    elif strategy_id == "s8":
        for i in range(22, n):
            prev = bars[i - 1]
            prev_prev = bars[i - 2]
            prev_pct = prev["pct"] / 100
            ma20_i = ma20[i]
            if not ma20_i:
                continue
            aligned = all(x is not None for x in (ma5[i - 1], ma10[i - 1], ma20[i - 1]))
            if (
                aligned
                and ma5[i - 1] > ma10[i - 1] > ma20[i - 1]
                and
                -0.05 <= prev_pct <= -0.003
                and prev["volume"] < prev_prev["volume"]
                and opens[i] < closes[i - 1] < closes[i]
                and closes[i] > ma20_i
            ):
                entry = closes[i] * (1 + COSTS["slippage"])
                params = STRATEGIES["s8"]["params"]
                exit_result = _exit_trade(
                    bars, i, entry, entry * (1 + params["take_profit"]),
                    entry * (1 - params["stop_loss"]), params["max_hold"],
                )
                if exit_result:
                    yield bars[i]["date"], entry, i, *exit_result


def _add_costs(gross_return: float) -> float:
    return gross_return - COSTS["commission"] * 2 - COSTS["stamp_duty"] - COSTS["slippage"] * 2


def _collect_raw_trades(engine, strategy_id: str) -> list[dict]:
    trades = []
    for stock in engine.universe:
        bars = engine.bars[stock["code"]]
        opens = [b["open"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        ma5 = sma(closes, 5)
        ma10 = sma(closes, 10)
        ma20 = sma(closes, 20)
        volume_ma5 = sma(volumes, 5)
        for entry_date, entry, entry_idx, exit_date, exit_price, hold_days in _signal_for_strategy(
            strategy_id, bars, opens, highs, lows, closes, volumes, ma5, ma10, ma20
        ):
            gross = exit_price / entry - 1
            net = _add_costs(gross)
            trades.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "entry_price": round(entry, 3),
                    "exit_price": round(exit_price, 3),
                    "pnl_pct": round(net * 100, 3),
                    "holding_days": hold_days,
                    "strategy_id": strategy_id,
                }
            )
    trades.sort(key=lambda t: (t["entry_date"], t["code"]))
    return trades


def _execute_portfolio(raw_trades, engine_dates, capital, position_pct=0.1, max_positions=5):
    """Apply the single-position sizing rule: 10% per trade, at most 5 open trades."""
    if not raw_trades:
        return [], []
    entries_by_date = {}
    for trade in raw_trades:
        entries_by_date.setdefault(trade["entry_date"], []).append(trade)

    start = raw_trades[0]["entry_date"]
    end = max(t["exit_date"] for t in raw_trades)
    positions = []
    executed = []
    curve = []
    equity = capital
    peak = capital
    max_drawdown = 0.0
    for day in engine_dates:
        if day < start or day > end:
            continue
        remaining = []
        for position in positions:
            if position["exit_date"] <= day:
                executed.append(position)
                equity += capital * position_pct * position["pnl_pct"] / 100.0
                peak = max(peak, equity)
                max_drawdown = min(max_drawdown, equity / peak - 1 if peak else 0)
                curve.append(
                    {
                        "date": position["exit_date"],
                        "equity": round(equity, 2),
                        "code": position["code"],
                    }
                )
            else:
                remaining.append(position)
        positions = remaining
        for trade in entries_by_date.get(day, []):
            if len(positions) < max_positions:
                positions.append(trade)
    return executed, curve


def _metrics_from_trades(trades, capital, curve):
    n = len(trades)
    if not n:
        return {k: 0 for k in ("trades", "win_rate", "profit_factor", "avg_win", "avg_loss", "total_return", "annual_return", "max_drawdown", "sharpe", "avg_holding")}
    pnls = [t["pnl_pct"] / 100 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / n
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0
    total_return = (curve[-1]["equity"] / capital - 1) if curve else 0.0
    peak = capital
    max_drawdown = 0.0
    for point in curve:
        peak = max(peak, point["equity"])
        max_drawdown = min(max_drawdown, point["equity"] / peak - 1)
    try:
        first = datetime.strptime(trades[0]["entry_date"], "%Y-%m-%d")
        last = datetime.strptime(trades[-1]["entry_date"], "%Y-%m-%d")
        years = max((last - first).days / 365.0, 0.25)
        annual_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1
    except Exception:
        annual_return = 0.0
    avg_holding = sum(t["holding_days"] for t in trades) / n
    sharpe = 0.0
    if n > 1:
        mean_pnl = sum(pnls) / n
        std = (sum((p - mean_pnl) ** 2 for p in pnls) / (n - 1)) ** 0.5
        if std:
            try:
                years = max((datetime.strptime(trades[-1]["entry_date"], "%Y-%m-%d") - datetime.strptime(trades[0]["entry_date"], "%Y-%m-%d")).days / 365.0, 0.25)
                trades_per_year = n / years
                sharpe = (mean_pnl / std) * (trades_per_year ** 0.5)
            except Exception:
                sharpe = 0.0
    return {
        "trades": n,
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win * 100, 2),
        "avg_loss": round(avg_loss * 100, 2),
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "max_drawdown": round(abs(max_drawdown) * 100, 2),
        "sharpe": round(sharpe, 2),
        "avg_holding": round(avg_holding, 1),
    }


def run_backtest(engine, strategy_id: str, capital: float = 1_000_000.0) -> dict:
    strategy = STRATEGIES[strategy_id]
    raw_trades = _collect_raw_trades(engine, strategy_id)
    executed, curve = _execute_portfolio(raw_trades, engine.dates, capital)
    metrics = _metrics_from_trades(executed, capital, curve)
    if not executed:
        metrics["trades"] = 0
        metrics["win_rate"] = 0
    return {
        "strategy_id": strategy_id,
        "strategy_name": strategy["name"],
        "win_rate": metrics["win_rate"],
        "metrics": metrics,
        "trades": executed[:80],
        "trade_count": len(executed),
        "all_signal_count": len(raw_trades),
        "equity_curve": curve,
        "costs": COSTS,
        "position_rule": {"position_pct": 0.1, "max_positions": 5},
        "note": "日线近似回测；按单仓 10%、最多 5 仓执行，用于策略胜率与风险基准。",
    }


def run_all_backtests(engine, capital=1_000_000.0):
    return {sid: run_backtest(engine, sid, capital) for sid in STRATEGY_ORDER}
