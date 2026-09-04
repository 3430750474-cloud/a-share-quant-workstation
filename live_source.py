"""Optional Tencent/Eastmoney live data adapter.

The application stays fully functional in offline simulator mode; when started
with ``--live`` this module supplies real A-share snapshots and K-line history.
"""

from __future__ import annotations

import time

import requests


EASTMONEY_ULIST = "https://push2.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
TENCENT_URL = "http://qt.gtimg.cn/q="
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def _secid(code: str) -> str:
    return f"1.{code}" if code.startswith(("6", "9")) else f"0.{code}"


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tencent_symbol(code: str) -> str:
    return f"sh{code}" if code.startswith(("6", "9")) else f"sz{code}"


def fetch_tencent_quotes(codes, timeout=8):
    """Fetch current quotes through the same Tencent feed used by many apps."""
    if not codes:
        return {}
    rows = {}
    step = 40
    for start in range(0, len(codes), step):
        chunk = codes[start : start + step]
        query = ",".join(_tencent_symbol(code) for code in chunk)
        try:
            response = requests.get(
                TENCENT_URL + query, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}
            )
            text = response.content.decode("gbk", errors="ignore")
        except Exception:
            continue
        for line in text.split(";"):
            if "=" not in line or line.startswith("v_pv_"):
                continue
            try:
                parts = line.split("=", 1)[1].strip(chr(34)).split("~")
            except Exception:
                continue
            if len(parts) < 50:
                continue
            code = str(parts[2] or "")
            if not code:
                continue
            rows[code] = {
                "code": code,
                "name": parts[1],
                "price": _float(parts[3]),
                "prev_close": _float(parts[4]),
                "open": _float(parts[5]),
                "volume": int(_float(parts[6]) * 100),
                "amount": _float(parts[37]) * 1e4,
                "turnover": _float(parts[38]),
                "pe": _float(parts[39]),
                "volume_ratio": _float(parts[49]),
                "high": _float(parts[33]),
                "low": _float(parts[34]),
                "change": _float(parts[31]),
                "change_pct": _float(parts[32]),
                "float_cap": _float(parts[45]),
                "pb": _float(parts[46]),
                "limit_up": _float(parts[47]),
                "limit_down": _float(parts[48]),
            }
    return rows


def fetch_eastmoney_quotes(codes, timeout=8):
    """Fetch current quotes for known demo codes from Eastmoney."""
    if not codes:
        return {}
    fields = "f12,f14,f2,f3,f4,f5,f6,f8,f10,f15,f16,f17,f18,f20,f21,f23,f9"
    rows = {}
    step = 20
    for start in range(0, len(codes), step):
        chunk = codes[start : start + step]
        secids = ",".join(_secid(code) for code in chunk)
        params = {
            "fltt": 2,
            "secids": secids,
            "fields": fields,
        }
        data = None
        for attempt in range(2):
            try:
                response = requests.get(
                    EASTMONEY_ULIST, params=params, timeout=timeout, headers=HEADERS
                )
                data = response.json()
                if data and data.get("rc") == 0:
                    break
            except Exception:
                data = None
            time.sleep(0.2)
        if not data or data.get("rc") != 0:
            continue
        for item in (data.get("data") or {}).get("diff") or []:
            code = str(item.get("f12") or "")
            if not code:
                continue
            rows[code] = {
                "code": code,
                "name": item.get("f14") or "",
                "price": _float(item.get("f2")),
                "change_pct": _float(item.get("f3")),
                "change": _float(item.get("f4")),
                "volume": int(_float(item.get("f5")) * 100),
                "amount": _float(item.get("f6")),
                "turnover": _float(item.get("f8")),
                "pe": _float(item.get("f9")),
                "volume_ratio": _float(item.get("f10")),
                "high": _float(item.get("f15")),
                "low": _float(item.get("f16")),
                "open": _float(item.get("f17")),
                "prev_close": _float(item.get("f18")),
                "float_cap": _float(item.get("f21")) / 1e8,
                "pb": _float(item.get("f23")),
                "limit_up": None,
                "limit_down": None,
            }
    return rows


def fetch_quotes(codes, timeout=8):
    """Fetch real quotes: Tencent first, Eastmoney fallback for missing codes."""
    rows = fetch_tencent_quotes(codes, timeout)
    missing = [code for code in codes if code not in rows]
    if missing:
        rows.update(fetch_eastmoney_quotes(missing, timeout))
    return rows


def fetch_kline(code, period="day", limit=500, timeout=12):
    """Return normalized daily or minute bars from Eastmoney."""
    klt = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "60m": 60,
        "day": 101,
        "week": 102,
    }.get(period, 101)
    params = {
        "secid": _secid(code),
        "klt": klt,
        "fqt": 1,
        "beg": "20200101",
        "end": "20500101",
        "lmt": min(limit, 800),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    }
    try:
        response = requests.get(
            EASTMONEY_KLINE, params=params, timeout=timeout, headers=HEADERS
        )
        data = response.json()
    except Exception:
        return []
    lines = ((data or {}).get("data") or {}).get("klines") or []
    bars = []
    for line in lines:
        parts = line.split(",")
        if len(parts) < 11:
            continue
        volume_hand = _float(parts[5])
        bars.append(
            {
                "date": parts[0],
                "open": _float(parts[1]),
                "close": _float(parts[2]),
                "high": _float(parts[3]),
                "low": _float(parts[4]),
                "volume": int(volume_hand * 100),
                "amount": _float(parts[6]),
                "pct": _float(parts[8]),
                "turnover": _float(parts[10]),
            }
        )
    return bars
