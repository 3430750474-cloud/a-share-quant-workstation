"""Fetch a liquid main-board A-share universe from Eastmoney and save it."""

from __future__ import annotations

import json
import pathlib
import time

import requests


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "mainboard_stocks.json"
URL = "https://push2.eastmoney.com/api/qt/clist/get"
PREFIXES = {"600", "601", "603", "605", "000", "001", "002", "003"}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def fetch_mainboard(limit: int = 900) -> list[dict]:
    rows = []
    seen = set()
    if OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except Exception:
            existing = []
        for row in existing:
            rows.append(row)
            seen.add(str(row.get("code")))
    page = 1
    while len(rows) < limit:
        params = {
            "pn": page,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f6",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f2,f6,f12,f14,f100",
        }
        diff = []
        for attempt in range(3):
            try:
                response = requests.get(
                    URL, params=params, timeout=12, headers=HEADERS
                )
                data = response.json()
                diff = ((data.get("data") or {}).get("diff")) or []
                if diff:
                    break
            except Exception:
                diff = []
            time.sleep(0.8)
        if not diff:
            break
        for item in diff:
            code = str(item.get("f12") or "")
            name = str(item.get("f14") or "")
            if code in seen:
                continue
            if code[:3] not in PREFIXES:
                continue
            if "ST" in name.upper() or "退" in name:
                continue
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "sector": str(item.get("f100") or "综合"),
                    "amount": float(item.get("f6") or 0),
                }
            )
            seen.add(code)
        page += 1
        time.sleep(0.4)
    return rows[:limit]


def main():
    rows = fetch_mainboard(600)
    if len(rows) < 50:
        raise SystemExit("fetch failed: not enough rows collected")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(rows, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"saved {len(rows)} main-board stocks to {OUTPUT}")


if __name__ == "__main__":
    main()
