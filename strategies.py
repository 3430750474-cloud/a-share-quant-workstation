"""Short-term strategies and the live signal screen."""

from __future__ import annotations

from indicators import rolling_gain, sma


STRATEGY_ORDER = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]


STRATEGIES = {
    "s1": {
        "id": "s1",
        "name": "竞价弱转强",
        "short": "弱转强",
        "tag": "开盘博弈",
        "risk": "高",
        "window": "09:15-09:25 竞价 / 09:30-09:35 执行",
        "objective": "昨日缩量阴线但趋势未坏，今日竞价由弱转强，博开盘承接。",
        "screen_conditions": [
            "昨日收阴，跌幅不超过 5%，收盘仍在 MA5/MA10 上方",
            "09:20-09:25 竞价价连续抬升",
            "09:25 开盘涨幅落在 +2%~+5%",
            "竞价成交额不低于 500 万元",
        ],
        "buy_rule": "09:30-09:35 回踩不破开盘价 1.5% 时买入；高开超 6% 或一字涨停跳过。",
        "sell_rule": "T+1 达 +4%~+6% 止盈，跌破买入价 3% 止损，09:45 前站不上均价线主动减仓。",
        "params": {
            "open_floor": 0.02,
            "open_ceil": 0.055,
            "take_profit": 0.05,
            "stop_loss": 0.03,
            "max_hold": 1,
        },
    },
    "s2": {
        "id": "s2",
        "name": "强势回踩低吸",
        "short": "回踩低吸",
        "tag": "均线支撑",
        "risk": "中",
        "window": "09:45-10:30 观察与买入",
        "objective": "短线强势股首次回踩 5 日线，在量价企稳点低吸。",
        "screen_conditions": [
            "昨收站上 MA5，MA5≥MA10≥MA20",
            "近 5 日涨幅 6%~25%",
            "日均成交额不低于 2 亿元",
            "盘中下探 MA5±0.5% 后由 5 分钟阳线收回",
        ],
        "buy_rule": "09:45-10:30 回踩 MA5 后收回即买入；高开超 4% 或跌破后不再收回则放弃。",
        "sell_rule": "T+1 达 +4%~+6% 止盈，跌破买入价 3% 止损，最长持有 2 个交易日。",
        "params": {
            "ma_window": 5,
            "pullback_tolerance": 0.005,
            "take_profit": 0.05,
            "stop_loss": 0.03,
            "max_hold": 2,
        },
    },
    "s3": {
        "id": "s3",
        "name": "平台放量突破",
        "short": "平台突破",
        "tag": "动量突破",
        "risk": "中",
        "window": "10:00-11:00 / 13:00-14:00",
        "objective": "识别窄幅整理平台，捕捉放量向上突破的启动段。",
        "screen_conditions": [
            "前 20 日高低点振幅不超过 18%",
            "5 分钟 K 线收盘突破 20 日最高价 1.005 倍",
            "突破 5 分钟量不低于此前 20 日同时段均量 2 倍",
            "距涨停不足 3% 的候选跳过",
        ],
        "buy_rule": "突破确认后跟随买入，不做涨停价追单。",
        "sell_rule": "T+1 达 +5%~+8% 止盈，回落跌破突破价且 5 分钟不回补止损，最长持有 3 个交易日。",
        "params": {
            "range_limit": 0.18,
            "break_buffer": 0.005,
            "volume_multiple": 2.0,
            "take_profit": 0.065,
            "stop_loss": 0.025,
            "max_hold": 3,
        },
    },
    "s4": {
        "id": "s4",
        "name": "尾盘强势潜伏",
        "short": "尾盘潜伏",
        "tag": "隔夜溢价",
        "risk": "中高",
        "window": "14:25-14:45 筛选 / 14:45-14:57 买入",
        "objective": "选择尾盘维持强度、未封板的强势股，博次日高开溢价。",
        "screen_conditions": [
            "涨幅主板 2%~7%，双创板 4%~12%",
            "现价不低于分时 VWAP",
            "日内位置处于当日区间 75% 分位以上",
            "最近 20 分钟量能明显放大且未跳水",
        ],
        "buy_rule": "14:45-14:57 分批买入，最后一笔安排在 14:55 后。",
        "sell_rule": "T+1 高开 3% 以上 09:30-09:35 卖出；否则 +3% 止盈、跌破 2.5% 止损，10:30 前走弱时间止损。",
        "params": {
            "min_pct": 0.025,
            "max_pct": 0.07,
            "take_profit": 0.035,
            "stop_loss": 0.025,
            "max_hold": 1,
        },
    },
    "s5": {
        "id": "s5",
        "name": "强势股首阴反包",
        "short": "首阴反包",
        "tag": "情绪修复",
        "risk": "高",
        "window": "13:30-14:30 确认反包后执行",
        "objective": "龙头首次分歧缩量回踩，等待午后分时重新走强。",
        "screen_conditions": [
            "前 5 日累计涨幅不低于 15%，其间至少一次涨停/大涨",
            "昨日首阴，跌幅 2%~7% 且未封跌停",
            "昨日量缩至前一日 0.8 倍以下",
            "今日午后 5 分钟 K 线站回昨收且现价高于 VWAP",
        ],
        "buy_rule": "午后站回昨收确认反包后买入，持续走弱不参与。",
        "sell_rule": "T+1 达 +5%~+7% 止盈，跌破买入价 4% 止损，最长持有 2 个交易日。",
        "params": {
            "streak_gain": 0.15,
            "pullback_floor": -0.07,
            "pullback_ceil": -0.02,
            "take_profit": 0.06,
            "stop_loss": 0.04,
            "max_hold": 2,
        },
    },
    "s6": {
        "id": "s6",
        "name": "多头趋势回踩",
        "short": "趋势回踩",
        "tag": "趋势低吸",
        "risk": "中",
        "window": "10:00-11:30 / 13:00-14:30",
        "objective": "MA20 走平转上、MA20 高于 MA60，趋势主线缩量回踩 10 日线后确认。",
        "screen_conditions": [
            "MA20 高于 MA60 且近 5 日上行",
            "昨收站稳 MA10，今日回踩 MA10±0.5%",
            "回踩后分时收回 MA10 上方并高于 VWAP",
            "未跌破 MA20，未靠近涨停",
        ],
        "buy_rule": "回踩 MA10 收回确认后买入；跌破 MA20 或无法站回则放弃。",
        "sell_rule": "T+1 达 +4% 止盈，跌破买入价 2% 止损，最长持有 2 个交易日。",
        "params": {
            "ma_slow": 60,
            "take_profit": 0.04,
            "stop_loss": 0.02,
            "max_hold": 2,
        },
    },
    "s7": {
        "id": "s7",
        "name": "均线粘合突破",
        "short": "粘合突破",
        "tag": "趋势启动",
        "risk": "中",
        "window": "10:00-11:00 / 13:00-14:00",
        "objective": "捕捉短期均线粘合后放量向上的二次启动段。",
        "screen_conditions": [
            "MA5、MA10、MA20 相互间距不超过 1.2%",
            "10 日平台振幅不超过 12%",
            "盘中放量突破 10 日最高价 1.003 倍",
            "量比不低于 1.8，未触涨停",
        ],
        "buy_rule": "突破 10 日平台并放量确认后买入。",
        "sell_rule": "T+1 达 +5% 止盈，跌破突破平台 2.5% 止损，最长持有 3 个交易日。",
        "params": {
            "range_limit": 0.12,
            "volume_multiple": 1.8,
            "take_profit": 0.05,
            "stop_loss": 0.025,
            "max_hold": 3,
        },
    },
    "s8": {
        "id": "s8",
        "name": "缩量回调反包",
        "short": "回调反包",
        "tag": "缩量修复",
        "risk": "中",
        "window": "09:45-10:30 / 13:00-14:30",
        "objective": "短线回落缩量后分时反包，博趋势延续修复。",
        "screen_conditions": [
            "昨收为阴线且跌幅不超过 5%",
            "昨日成交量小于前日",
            "今日低开后 5 分钟站回昨收",
            "现价高于 VWAP，未破 MA20",
        ],
        "buy_rule": "低开翻红并站回昨收后买入；午后持续走弱不参与。",
        "sell_rule": "T+1 达 +2% 即止盈，跌破买入价 3% 止损，最长持有 2 个交易日。",
        "params": {
            "pullback_floor": -0.05,
            "take_profit": 0.02,
            "stop_loss": 0.03,
            "max_hold": 2,
        },
    },
}


def strategy_list():
    return [STRATEGIES[sid] for sid in STRATEGY_ORDER]


def _closes(bars):
    return [b["close"] for b in bars]


def _ma_list(bars, period):
    return sma(_closes(bars), period)


def _quality(score: float, volume_ratio: float) -> str:
    if score >= 82 or (score >= 70 and volume_ratio >= 1.9):
        return "高"
    if score >= 56 and volume_ratio >= 1.15:
        return "合格"
    return "差"


def _strength(score: float) -> str:
    if score >= 76:
        return "强"
    if score >= 58:
        return "中"
    return "弱"


def classify_quality(score: float, volume_ratio: float) -> str:
    return _quality(score, volume_ratio)


def classify_strength(score: float) -> str:
    return _strength(score)


def _action(quality: str, strength: str) -> str:
    if quality == "高" and strength == "强":
        return "优先执行"
    if quality in ("高", "合格"):
        return "分批介入"
    if strength == "中":
        return "盘中观察"
    return "放弃或等二次确认"


def _limits(stock, quote):
    board_pct = 9.6 if stock["board"] == "主板" else 19.6
    return board_pct


def screen_one(stock, bars, quote):
    """Return one signal dict for a stock or None."""
    closes = _closes(bars)
    if len(bars) < 70:
        return None
    prev = bars[-1]
    prev2 = bars[-2]
    close = closes[-1]
    ma5 = sma(closes, 5)[-1]
    ma10 = sma(closes, 10)[-1]
    ma20 = sma(closes, 20)[-1]
    ma60 = sma(closes, 60)[-1]
    ma20_prev5 = sma(closes, 20)[-6]
    gain5 = closes[-1] / closes[-6] - 1 if len(closes) >= 6 else 0.0
    gain5_prev = closes[-2] / closes[-7] - 1 if len(closes) >= 7 else 0.0
    prior20_high = max(b["high"] for b in bars[-21:-1]) if len(bars) >= 21 else 0
    prior20_low = min(b["low"] for b in bars[-21:-1]) if len(bars) >= 21 else 0
    prior10_high = max(b["high"] for b in bars[-11:-1]) if len(bars) >= 11 else 0
    prior10_low = min(b["low"] for b in bars[-11:-1]) if len(bars) >= 11 else 0
    range_width = (prior20_high - prior20_low) / prior20_low if prior20_low else 0
    range10_width = (
        (prior10_high - prior10_low) / prior10_low if prior10_low else 0
    )
    today_pct = quote["change_pct"]
    pct = today_pct / 100.0
    vwap_ratio = quote["price"] / quote["vwap"] - 1
    day_high = quote["high"]
    day_low = quote["low"]
    position = (
        (quote["price"] - day_low) / (day_high - day_low)
        if day_high > day_low
        else 0.5
    )
    vol_ratio = quote["volume_ratio"]
    stock["latest_close"] = close

    signals = []

    # S1: weak yesterday, auction gap-up and holding strength today.
    if (
        -5.0 <= prev["pct"] <= -0.1
        and prev["close"] > (ma10 or 0)
        and 0.02 <= pct <= 0.055
        and not quote["near_limit_up"]
        and prev2["volume"] > prev["volume"]
    ):
        score = 58.0
        score += 12 if prev["close"] >= ma5 else 0
        score += 10 if quote["price"] >= quote["open"] else -8
        score += 8 if vol_ratio >= 1.6 else 0
        score += 6 if pct >= 0.035 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        signals.append(
            {
                "strategy_id": "s1",
                "strategy_name": "竞价弱转强",
                "window": "09:30-09:35",
                "entry_price": round(quote["open"], 3),
                "take_price": round(quote["open"] * 1.05, 3),
                "stop_price": round(quote["open"] * 0.97, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"昨日收阴 {prev['pct']:.1f}%，量能萎缩",
                    f"今日涨幅 {quote['change_pct']:.1f}%，开盘承接",
                    f"量比 {vol_ratio:.1f}，站稳昨日收盘上方",
                ],
            }
        )

    # S2: strong stock pullback to MA5 with recovery above it.
    prev_above_ma5 = prev["close"] >= ma5
    aligned = bool(ma5 and ma10 and ma20 and ma5 >= ma10 >= ma20)
    if (
        prev_above_ma5
        and aligned
        and 0.06 <= gain5_prev <= 0.25
        and -0.04 <= pct <= 0.02
        and day_low <= ma5 * 1.008
        and quote["price"] > ma5 * 0.995
        and not quote["near_limit_down"]
    ):
        score = 60.0
        score += 12 if quote["price"] >= ma5 else 0
        score += 10 if prev["close"] > prev["open"] else 0
        score += 8 if vol_ratio >= 1.5 else 0
        score += 6 if position >= 0.45 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(max(quote["price"], ma5 * 1.002), 3)
        signals.append(
            {
                "strategy_id": "s2",
                "strategy_name": "强势回踩低吸",
                "window": "09:45-10:30",
                "entry_price": entry,
                "take_price": round(entry * 1.05, 3),
                "stop_price": round(entry * 0.97, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"5 日涨幅 {gain5_prev * 100:.1f}%，均线多头",
                    f"回踩 MA5 {ma5:.2f} 后回升",
                    f"现价 {quote['price']:.2f}，日内修复",
                ],
            }
        )

    # S3: narrow platform, fresh breakout with volume.
    broke = quote["high"] >= prior20_high * 1.005 and quote["price"] > prior20_high
    if (
        range_width <= 0.18
        and broke
        and not quote["near_limit_up"]
        and vol_ratio >= 1.4
        and pct >= 0.01
    ):
        score = 60.0
        score += 10 if range_width <= 0.12 else 0
        score += 12 if vol_ratio >= 2.0 else 0
        score += 8 if pct >= 0.03 else 0
        score += 6 if position >= 0.7 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(quote["price"], 3)
        signals.append(
            {
                "strategy_id": "s3",
                "strategy_name": "平台放量突破",
                "window": "10:00-11:00 / 13:00-14:00",
                "entry_price": entry,
                "take_price": round(entry * 1.06, 3),
                "stop_price": round(prior20_high * 0.985, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"平台振幅 {range_width * 100:.1f}%，20 日最高 {prior20_high:.2f}",
                    f"突破价 {quote['high']:.2f}，量比 {vol_ratio:.1f}",
                    f"今日涨幅 {quote['change_pct']:.1f}%，未触涨停",
                ],
            }
        )

    # S4: late-session strength near the day high above VWAP.
    board_pct = _limits(stock, quote)
    min_pct = 0.04 if stock["board"] == "双创" else 0.025
    max_pct = 0.12 if stock["board"] == "双创" else 0.07
    if (
        min_pct <= pct <= max_pct
        and vwap_ratio >= 0
        and position >= 0.72
        and vol_ratio >= 1.2
        and not quote["near_limit_up"]
    ):
        score = 62.0
        score += 10 if vwap_ratio >= 0.004 else 0
        score += 10 if position >= 0.88 else 0
        score += 8 if pct >= 0.04 else 0
        score += 6 if vol_ratio >= 1.8 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(quote["price"], 3)
        signals.append(
            {
                "strategy_id": "s4",
                "strategy_name": "尾盘强势潜伏",
                "window": "14:45-14:57",
                "entry_price": entry,
                "take_price": round(entry * 1.035, 3),
                "stop_price": round(entry * 0.975, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"涨幅 {quote['change_pct']:.1f}%，未封板",
                    f"日内分位 {position * 100:.0f}%，高于 VWAP",
                    f"量比 {vol_ratio:.1f}，尾盘保持强度",
                ],
            }
        )

    # S5: strong leader's first pullback followed by afternoon recovery.
    volume_shrink = prev["volume"] < prev2["volume"] * 0.8
    rebound = quote["price"] >= prev["close"] and pct >= -0.01 and position > 0.55
    if (
        gain5_prev >= 0.12
        and -7.0 <= prev["pct"] <= -2.0
        and volume_shrink
        and rebound
        and not quote["near_limit_down"]
    ):
        score = 60.0
        score += 14 if gain5_prev >= 0.18 else 0
        score += 10 if quote["price"] > prev["close"] else 0
        score += 8 if vwap_ratio >= 0 else 0
        score += 6 if vol_ratio >= 1.3 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(quote["price"], 3)
        signals.append(
            {
                "strategy_id": "s5",
                "strategy_name": "强势股首阴反包",
                "window": "13:30-14:30",
                "entry_price": entry,
                "take_price": round(entry * 1.06, 3),
                "stop_price": round(entry * 0.96, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"前 5 日涨幅 {gain5_prev * 100:.1f}%，强势特征",
                    f"昨日首阴 {prev['pct']:.1f}%，缩量 {prev['volume'] / prev2['volume']:.0%}",
                    f"今日回到昨收上方，午后确认反包",
                ],
            }
        )

    # S6: MA20/MA60 trend low-absorption on a pullback to MA10.
    ma_spread = (
        max(ma5, ma10, ma20) / min(ma5, ma10, ma20) - 1
        if min(ma5, ma10, ma20)
        else 99
    )
    trend_up = bool(
        ma20 and ma60 and ma20_prev5 and ma20 > ma60 and ma20 > ma20_prev5
    )
    if (
        trend_up
        and prev["close"] >= ma10
        and day_low <= ma10 * 1.006
        and quote["price"] >= ma10 * 0.995
        and quote["price"] > ma20
        and -0.03 <= pct <= 0.02
        and not quote["near_limit_down"]
        and not quote["near_limit_up"]
    ):
        score = 62.0
        score += 12 if quote["price"] >= ma10 else 0
        score += 10 if quote["price"] >= quote["vwap"] else 0
        score += 8 if prev["volume"] < prev2["volume"] else 0
        score += 6 if ma_spread <= 0.06 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(max(quote["price"], ma10 * 1.002), 3)
        signals.append(
            {
                "strategy_id": "s6",
                "strategy_name": "多头趋势回踩",
                "window": "10:00-11:30 / 13:00-14:30",
                "entry_price": entry,
                "take_price": round(entry * 1.04, 3),
                "stop_price": round(entry * 0.98, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"MA20 {ma20:.2f} 高于 MA60 {ma60:.2f} 且上行",
                    f"回踩 MA10 {ma10:.2f} 后企稳",
                    f"现价 {quote['price']:.2f}，站稳 VWAP",
                ],
            }
        )

    # S7: tight MA cluster then fresh 10-day breakout with volume.
    if (
        ma_spread <= 0.05
        and range10_width <= 0.12
        and quote["high"] >= prior10_high * 1.003
        and quote["price"] > prior10_high
        and vol_ratio >= 1.8
        and pct >= 0.01
        and not quote["near_limit_up"]
    ):
        score = 62.0
        score += 12 if ma_spread <= 0.025 else 0
        score += 12 if vol_ratio >= 2.4 else 0
        score += 8 if pct >= 0.03 else 0
        score += 6 if position >= 0.72 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(quote["price"], 3)
        signals.append(
            {
                "strategy_id": "s7",
                "strategy_name": "均线粘合突破",
                "window": "10:00-11:00 / 13:00-14:00",
                "entry_price": entry,
                "take_price": round(entry * 1.05, 3),
                "stop_price": round(prior10_high * 0.98, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"均线间距 {ma_spread * 100:.1f}%，粘合充分",
                    f"突破 10 日高点 {prior10_high:.2f}，量比 {vol_ratio:.1f}",
                    f"涨幅 {quote['change_pct']:.1f}%，放量启动",
                ],
            }
        )

    # S8: low-volume pullback reversed by the day's trend line.
    yesterday_shrink = prev["volume"] < prev2["volume"]
    reversed_back = (
        quote["open"] < prev["close"] <= quote["price"]
        and position > 0.5
        and quote["price"] > (ma20 or quote["price"])
    )
    if (
        -5.0 <= prev["pct"] <= -0.3
        and yesterday_shrink
        and reversed_back
        and not quote["near_limit_up"]
        and not quote["near_limit_down"]
    ):
        score = 60.0
        score += 12 if vwap_ratio >= 0 else 0
        score += 10 if prev["close"] >= (ma10 or 0) else 0
        score += 8 if position >= 0.75 else 0
        score += 6 if vol_ratio >= 1.2 else 0
        score = max(0, min(100, score))
        quality = _quality(score, vol_ratio)
        entry = round(quote["price"], 3)
        signals.append(
            {
                "strategy_id": "s8",
                "strategy_name": "缩量回调反包",
                "window": "09:45-10:30 / 13:00-14:30",
                "entry_price": entry,
                "take_price": round(entry * 1.02, 3),
                "stop_price": round(entry * 0.97, 3),
                "score": round(score, 1),
                "strength": _strength(score),
                "quality": quality,
                "action": _action(quality, _strength(score)),
                "reasons": [
                    f"昨日阴线 {prev['pct']:.1f}%，量能收缩",
                    f"今日低开站回昨收 {prev['close']:.2f}",
                    f"涨幅 {quote['change_pct']:.1f}%，确认反包",
                ],
            }
        )
    return signals


def screen_market(engine):
    """Refresh signals and attach quote info."""
    with engine._lock:
        signals = []
        signal_time = {
            "s1": "09:35",
            "s2": "09:55",
            "s3": "10:20",
            "s4": "14:52",
            "s5": "13:45",
            "s6": "10:30",
            "s7": "13:20",
            "s8": "10:10",
        }
        for stock in engine.universe:
            quote = engine.quotes[stock["code"]]
            found = screen_one(stock, engine.bars[stock["code"]], quote)
            for sig in found or []:
                signals.append(
                    {
                        **sig,
                        "code": stock["code"],
                        "name": stock["name"],
                        "sector": stock["sector"],
                        "board": stock["board"],
                        "price": quote["price"],
                        "change_pct": quote["change_pct"],
                        "volume_ratio": quote["volume_ratio"],
                        "time": signal_time.get(sig["strategy_id"], "10:30"),
                    }
                )
        engine.signals = signals
        engine.signal_version += 1
        return signals
