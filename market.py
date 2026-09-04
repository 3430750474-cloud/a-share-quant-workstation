"""Deterministic offline market simulator used to power the demo workspace."""

from __future__ import annotations

import math
import threading
import zlib
from datetime import date, timedelta

import numpy as np

from indicators import atr, boll, kdj, macd, rsi, sma
from stock_list import build_universe


def _business_days(count: int, end: date | None = None) -> list[str]:
    """Return `count` recent weekdays ending before today (no exchange holidays)."""
    end = end or date.today()
    days: list[str] = []
    cursor = end - timedelta(days=1)
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.strftime("%Y-%m-%d"))
        cursor -= timedelta(days=1)
    return list(reversed(days))


class MarketEngine:
    def __init__(self, history_days: int = 520):
        self.universe = build_universe()
        self.stock_index = {s["code"]: s for s in self.universe}
        self.dates = _business_days(history_days)
        self.bars: dict[str, list[dict]] = {}
        self.quotes: dict[str, dict] = {}
        self.snapshot_by_code: dict[str, dict] = {}
        self.signals: list[dict] = []
        self.signal_version = 0
        self.clock_minute = 10 * 60 + 32
        self.tick = 0
        self._lock = threading.RLock()
        self._generate_history()
        self._generate_quotes()

    # ---- data generation -------------------------------------------------
    def _seed(self, code: str) -> int:
        return zlib.crc32(code.encode("utf-8"))

    def _generate_history(self):
        count = len(self.dates)
        for stock in self.universe:
            code = stock["code"]
            seed = self._seed(code)
            rng = np.random.default_rng(seed)
            stock["base_price"] = round(7 + (seed % 940) / 10.0, 2)
            stock["pe"] = round(12 + (seed % 730) / 10.0, 1)
            stock["float_shares"] = float(2e8 + (seed % 4200) * 4.5e6)
            max_day_ret = 0.195 if stock["is_20cm"] else 0.098
            vol = 0.014 + (seed % 47) / 47.0 * 0.022
            drift = (seed % 250 - 108) / 100000.0
            phase = (seed % 628) / 100.0
            cycle_amp = (seed % 11) / 100.0 * vol * 2.6

            rets = rng.normal(0.0, vol, count)
            waves = np.sin(np.arange(count) / (18 + seed % 24) + phase) * cycle_amp
            rets = rets + waves + drift

            # Inject deterministic "leader first pullback" patterns for a
            # subset of the demo universe so S5 has enough historical samples.
            pattern_days = set()
            if seed % 17 < 6:
                step = 130 + (seed % 65)
                for start in range(60 + seed % 20, count - 12, step):
                    pattern_days.add(start + 5)
                    for j in range(5):
                        rets[start + j] = min(
                            max(rets[start + j] + 0.033, 0.012),
                            max_day_ret * 0.9,
                        )
                    rets[start + 5] = min(
                        max(rets[start + 5] - 0.055, -0.07), -0.02
                    )
                    rets[start + 6] = min(
                        max(rets[start + 6] + 0.036, 0.02),
                        max_day_ret * 0.85,
                    )
            rets = np.clip(rets, -max_day_ret * 0.96, max_day_ret * 0.96)

            closes: list[float] = []
            price = float(stock["base_price"])
            for ret in rets:
                price *= 1.0 + float(ret)
                price = max(0.8, price)
                closes.append(round(price, 3))

            avg_volume = float(stock["float_shares"]) * 0.012
            bars: list[dict] = []
            prev_close = float(stock["base_price"]) / (1.0 + sum(rets[:20]) / 20.0)
            for i, close in enumerate(closes):
                open_gap = float(rng.normal(0, vol * 0.42))
                open_price = prev_close * (1 + max(-0.06, min(0.06, open_gap)))
                high_gap = abs(float(rng.normal(0, vol * 0.55)))
                low_gap = abs(float(rng.normal(0, vol * 0.55)))
                high = max(open_price, close) * (1 + high_gap)
                low = min(open_price, close) * (1 - low_gap)
                volume = float(abs(rng.lognormal(math.log(avg_volume), 0.7)))
                amount = volume * (open_price + close + high + low) / 4.0
                pct = close / prev_close - 1.0 if prev_close else 0.0
                bars.append(
                    {
                        "date": self.dates[i],
                        "open": round(open_price, 3),
                        "high": round(max(high, open_price, close), 3),
                        "low": round(max(0.01, min(low, open_price, close)), 3),
                        "close": close,
                        "volume": int(volume),
                        "amount": round(amount, 2),
                        "pct": round(pct * 100, 2),
                        "turnover": round(volume / stock["float_shares"] * 100, 2),
                    }
                )
                prev_close = close
            for drop_idx in pattern_days:
                if drop_idx >= len(bars) or drop_idx == 0:
                    continue
                prev_run = bars[drop_idx - 1]
                bars[drop_idx]["volume"] = int(prev_run["volume"] * 0.55)
                bars[drop_idx]["amount"] = round(
                    bars[drop_idx]["amount"] * 0.55, 2
                )
                if drop_idx + 1 < len(bars):
                    recover = bars[drop_idx + 1]
                    recover["open"] = round(bars[drop_idx]["close"] * 0.99, 3)
                    recover["low"] = min(recover["low"], recover["open"])
                    recover["high"] = max(recover["high"], recover["close"])
            self.bars[code] = bars
            stock["latest_close"] = bars[-1]["close"]

    def _generate_quotes(self):
        archetypes = [
            {"pct": 6.2, "open": 4.8, "spread": 2.1, "strength": 1},
            {"pct": 3.8, "open": 2.4, "spread": 2.4, "strength": 1},
            {"pct": 2.1, "open": 0.9, "spread": 2.0, "strength": 0},
            {"pct": 0.8, "open": -0.2, "spread": 1.8, "strength": 0},
            {"pct": -0.9, "open": 0.6, "spread": 2.3, "strength": -1},
            {"pct": -2.6, "open": -1.1, "spread": 2.7, "strength": -1},
            {"pct": 4.6, "open": 0.4, "spread": 2.8, "strength": 1},
            {"pct": 7.6, "open": 3.0, "spread": 2.9, "strength": 1},
        ]
        for stock in self.universe:
            code = stock["code"]
            seed = self._seed(code)
            bars = self.bars[code]
            prev_close = bars[-1]["close"]
            profile = archetypes[seed % len(archetypes)]
            cap_pct = 9.6 if stock["board"] == "主板" else 19.6
            pct = min(profile["pct"], cap_pct - 0.5)
            open_pct = min(profile["open"], pct - 0.3)
            price = prev_close * (1 + pct / 100.0)
            open_price = prev_close * (1 + open_pct / 100.0)
            upper_spread = abs(profile["spread"]) / 100.0
            lower_spread = abs(profile["spread"]) / 140.0
            high = max(price, open_price) * (1 + upper_spread)
            low = min(price, open_price) * (1 - lower_spread)
            float_shares = stock["float_shares"]
            base_volume = float(bars[-1]["volume"])
            volume = base_volume * (0.25 + abs(pct) / 9.0)
            vwap = (open_price + price + high + low) / 4.0
            amount = volume * vwap
            limit_up = prev_close * (1.1 if stock["board"] == "主板" else 1.2)
            limit_down = prev_close * (0.9 if stock["board"] == "主板" else 0.8)
            self.quotes[code] = {
                "code": code,
                "name": stock["name"],
                "sector": stock["sector"],
                "prev_close": round(prev_close, 3),
                "open": round(open_price, 3),
                "price": round(price, 3),
                "high": round(high, 3),
                "low": round(low, 3),
                "vwap": round(vwap, 3),
                "change_pct": round((price / prev_close - 1) * 100, 2),
                "volume": int(volume),
                "amount": round(amount, 2),
                "volume_ratio": round(1.0 + abs(pct) / 3.0, 2),
                "turnover": round(volume / float_shares * 100, 2),
                "float_cap": round(float_shares * price / 1e8, 1),
                "limit_up": round(limit_up, 3),
                "limit_down": round(limit_down, 3),
                "near_limit_up": price >= limit_up * 0.985,
                "near_limit_down": price <= limit_down * 1.015,
            }
        self.refresh_quotes_derived()

    def refresh_quotes_derived(self):
        """Recompute metrics that depend on the moving simulated price."""
        for code, quote in self.quotes.items():
            stock = self.stock_index[code]
            prev_close = quote["prev_close"]
            price = quote["price"]
            quote["change_pct"] = round((price / prev_close - 1) * 100, 2)
            quote["float_cap"] = round(stock["float_shares"] * price / 1e8, 1)
            quote["pe"] = round(stock["pe"] * price / stock["latest_close"], 1)
            quote["pb"] = round(1.1 + (self._seed(code) % 700) / 220.0, 2)

    def apply_live_quotes(self, live_rows):
        """Overlay Eastmoney real-time snapshots onto the working quote table."""
        if not live_rows:
            return
        with self._lock:
            for code, row in live_rows.items():
                quote = self.quotes.get(code)
                if quote is None or not row.get("price"):
                    continue
                stock = self.stock_index[code]
                prev_close = row.get("prev_close") or quote["prev_close"]
                if prev_close <= 0:
                    continue
                price = row["price"]
                limit_ratio = 1.1 if stock["board"] == "主板" else 1.2
                quote.update(
                    {
                        "name": row.get("name") or quote["name"],
                        "prev_close": round(prev_close, 3),
                        "open": round(row.get("open") or prev_close, 3),
                        "price": round(price, 3),
                        "high": round(row.get("high") or price, 3),
                        "low": round(row.get("low") or price, 3),
                        "change_pct": round(row.get("change_pct") or 0, 2),
                        "volume": int(row.get("volume") or quote["volume"]),
                        "amount": round(row.get("amount") or 0, 2),
                        "volume_ratio": round(row.get("volume_ratio") or 0, 2),
                        "turnover": round(row.get("turnover") or 0, 2),
                        "pe": row.get("pe"),
                        "pb": row.get("pb"),
                        "float_cap": round(row.get("float_cap") or 0, 1),
                        "limit_up": round(prev_close * limit_ratio, 3),
                        "limit_down": round(prev_close * (2 - limit_ratio), 3),
                        "near_limit_up": price >= prev_close * limit_ratio * 0.985,
                        "near_limit_down": price <= prev_close * (2 - limit_ratio) * 1.015,
                    }
                )
                if quote["volume"] > 0 and quote["amount"] > 0:
                    quote["vwap"] = round(quote["amount"] / quote["volume"], 3)

    # ---- technical data ---------------------------------------------------
    def indicator_snapshot(self, code: str, limit: int = 180):
        bars = self.bars[code]
        closes = [b["close"] for b in bars]
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        volumes = [b["volume"] for b in bars]
        cutoff = max(0, len(bars) - limit)
        return {
            "dates": [b["date"] for b in bars[cutoff:]],
            "bars": bars[cutoff:],
            "ma5": sma(closes, 5)[cutoff:],
            "ma10": sma(closes, 10)[cutoff:],
            "ma20": sma(closes, 20)[cutoff:],
            "ma60": sma(closes, 60)[cutoff:],
            "dif": macd(closes)[0][cutoff:],
            "dea": macd(closes)[1][cutoff:],
            "macd": macd(closes)[2][cutoff:],
            "kdj_k": kdj(highs, lows, closes)[0][cutoff:],
            "kdj_d": kdj(highs, lows, closes)[1][cutoff:],
            "kdj_j": kdj(highs, lows, closes)[2][cutoff:],
            "rsi": rsi(closes)[cutoff:],
            "boll_upper": boll(closes)[0][cutoff:],
            "boll_mid": boll(closes)[1][cutoff:],
            "boll_low": boll(closes)[2][cutoff:],
            "atr": atr(highs, lows, closes)[cutoff:],
            "vol_sma5": sma(volumes, 5)[cutoff:],
        }

    def daily_arrays(self, code: str):
        bars = self.bars[code]
        return {
            "dates": [b["date"] for b in bars],
            "open": [b["open"] for b in bars],
            "high": [b["high"] for b in bars],
            "low": [b["low"] for b in bars],
            "close": [b["close"] for b in bars],
            "volume": [b["volume"] for b in bars],
            "amount": [b["amount"] for b in bars],
            "pct": [b["pct"] for b in bars],
        }

    def minute_snapshot(self, code: str, interval: str = "5m", limit: int = 180):
        """Synthetic intraday replay used until a real minute feed is attached."""
        points_per_day = {"1m": 240, "5m": 48, "15m": 16, "30m": 8, "60m": 4}
        points = points_per_day.get(interval, 48)
        quote = self.quotes[code]
        live_day = {
            "date": date.today().strftime("%Y-%m-%d"),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["price"],
            "volume": quote["volume"],
            "amount": quote["amount"],
            "pct": quote["change_pct"],
            "turnover": quote["turnover"],
        }
        days = list(self.bars[code][-(max(2, limit // points + 2)) :]) + [live_day]
        if interval == "1m":
            days = days[-1:]
        result = []

        def time_label(index: int) -> str:
            minute = int(round((index + 0.5) * 240 / points))
            minute = min(239, minute)
            if minute < 120:
                total = 9 * 60 + 30 + minute
            else:
                total = 13 * 60 + (minute - 120)
            return f"{total // 60:02d}:{total % 60:02d}"

        for day in days:
            seed = self._seed(code) + int(day["date"].replace("-", ""))
            rng = np.random.default_rng(seed)
            day_open = day["open"]
            day_close = day["close"]
            day_high = day["high"]
            day_low = day["low"]
            alpha = np.linspace(0, 1, points)
            walk = np.r_[0.0, rng.normal(0, 1, points - 1)].cumsum()
            walk = walk - alpha * walk[-1]
            span = max(day_high - day_low, abs(day_close) * 0.004)
            path = day_open + (day_close - day_open) * alpha + walk * span * 0.38
            path[0] = day_open
            path[-1] = day_close
            path = np.maximum(path, 0.01)
            prev = day_open
            volumes = np.abs(rng.normal(1.0, 0.35, points))
            for i, price in enumerate(path):
                open_price = day_open if i == 0 else prev
                close_price = float(price)
                high_price = max(open_price, close_price)
                low_price = min(open_price, close_price)
                if i == 0:
                    high_price = max(high_price, day_high)
                if i == points - 1:
                    low_price = min(low_price, day_low)
                result.append(
                    {
                        "date": f"{day['date']} {time_label(i)}",
                        "open": round(open_price, 3),
                        "high": round(high_price, 3),
                        "low": round(low_price, 3),
                        "close": round(close_price, 3),
                        "volume": int(day["volume"] / points * float(volumes[i])),
                        "amount": round(
                            (day["amount"] or 0) / points * float(volumes[i]), 2
                        ),
                        "pct": day["pct"],
                        "turnover": (day.get("turnover") or 0) / points,
                        "replay": True,
                    }
                )
                prev = close_price

        result = result[-limit:]
        closes = [b["close"] for b in result]
        volumes = [b["volume"] for b in result]
        return {
            "dates": [b["date"] for b in result],
            "bars": result,
            "period": interval,
            "ma5": sma(closes, 5),
            "ma10": sma(closes, 10),
            "ma20": sma(closes, 20),
            "rsi": rsi(closes),
            "vol_sma5": sma(volumes, 5),
            "replay": True,
        }

    # ---- real-time simulation ---------------------------------------------
    def advance(self):
        """Advance the demo market a small step."""
        with self._lock:
            self.tick += 1
            self.clock_minute = min(15 * 60, self.clock_minute + 1)
            rng = np.random.default_rng(self.tick * 7919 + 17)
            for code, quote in self.quotes.items():
                stock = self.stock_index[code]
                board_pct = 9.6 if stock["board"] == "主板" else 19.6
                drift = float(rng.normal(0, 0.0028))
                old_price = quote["price"]
                price = old_price * (1 + drift)
                prev_close = quote["prev_close"]
                pct = (price / prev_close - 1) * 100
                if pct > board_pct or pct < -board_pct * 0.98:
                    price = old_price
                quote["price"] = round(price, 3)
                quote["high"] = max(quote["high"], quote["price"])
                quote["low"] = min(quote["low"], quote["price"])
                quote["volume"] = int(quote["volume"] * (1 + abs(drift) * 4))
                quote["amount"] = round(
                    quote["amount"] * (1 + abs(drift) * 4), 2
                )
            self.refresh_quotes_derived()

    # ---- serialization helpers --------------------------------------------
    def market_rows(self, codes=None):
        rows = []
        selected = self.quotes if codes is None else {
            k: v for k, v in self.quotes.items() if k in codes
        }
        for code, quote in selected.items():
            stock = self.stock_index[code]
            rows.append(
                {
                    **quote,
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "board": stock["board"],
                    "is_20cm": stock["is_20cm"],
                    "pe": quote.get("pe"),
                    "pb": quote.get("pb"),
                    "signal_count": sum(
                        1 for s in self.signals if s["code"] == code
                    ),
                }
            )
        return rows
