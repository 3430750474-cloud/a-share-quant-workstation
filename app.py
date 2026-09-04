"""Flask API for the A-share short-term quant workstation."""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import date, datetime
from http import HTTPStatus

from flask import Flask, Response, jsonify, request, send_from_directory

from backtest import run_backtest
from indicators import rsi, sma
import live_source
from market import MarketEngine
from strategies import STRATEGIES, STRATEGY_ORDER, screen_market


app = Flask(__name__, static_folder="static", static_url_path="/static")

# Flask 1.1 compatibility: route shortcuts were introduced in Flask 2.0.
if not hasattr(app, "get"):
    def _flask_get(rule, **options):
        return app.route(rule, methods=["GET"], **options)

    def _flask_post(rule, **options):
        return app.route(rule, methods=["POST"], **options)

    def _flask_delete(rule, **options):
        return app.route(rule, methods=["DELETE"], **options)

    app.get = _flask_get
    app.post = _flask_post
    app.delete = _flask_delete

LIVE_ENABLED = "--live" in sys.argv
engine = MarketEngine()
screen_market(engine)
LIVE_READY = False
if LIVE_ENABLED:
    try:
        live_rows = live_source.fetch_quotes(list(engine.quotes.keys()))
        engine.apply_live_quotes(live_rows)
        LIVE_READY = bool(live_rows)
    except Exception:
        LIVE_READY = False

WATCHLIST_DEFAULT = ["600519", "300750", "002230", "601127", "000063", "300308"]
watchlist = list(WATCHLIST_DEFAULT)
paper_cash = 1_000_000.0
paper_orders = []
paper_positions = {}

backtests = {}
backtest_lock = threading.Lock()
_paper_id = 0
_order_lock = threading.Lock()


def _market_clock_text():
    if LIVE_READY:
        return datetime.now().strftime("%H:%M")
    minute = engine.clock_minute
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _warm_backtests():
    time.sleep(0.8)
    with backtest_lock:
        for sid in STRATEGY_ORDER:
            try:
                backtests[sid] = run_backtest(engine, sid, 1_000_000.0)
            except Exception:
                backtests[sid] = None


def _simulation_loop():
    counter = 0
    while True:
        time.sleep(4.5 if LIVE_ENABLED else 2.4)
        try:
            if LIVE_ENABLED:
                rows = live_source.fetch_quotes(list(engine.quotes.keys()))
                if rows:
                    engine.apply_live_quotes(rows)
                screen_market(engine)
            else:
                engine.advance()
                counter += 1
                if counter % 3 == 0:
                    screen_market(engine)
        except Exception:
            pass


threading.Thread(target=_warm_backtests, daemon=True).start()
threading.Thread(target=_simulation_loop, daemon=True).start()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.after_request
def _no_store_static(response):
    if request.path == "/" or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


def _quote_payload(code):
    quote = engine.quotes[code]
    stock = engine.stock_index[code]
    return {**quote, "stock": stock, "clock": _market_clock_text()}


def _load_live_daily_bars(code: str) -> bool:
    """Replace synthetic bars with real Eastmoney daily history for a code."""
    if not LIVE_READY or code not in engine.stock_index:
        return False
    try:
        bars = live_source.fetch_kline(code, "day", 700)
        if len(bars) < 30:
            return False
        engine.bars[code] = bars
        engine.stock_index[code]["latest_close"] = bars[-1]["close"]
        return True
    except Exception:
        return False


@app.get("/api/meta")
def meta():
    signals = engine.signals
    rows = engine.market_rows()
    up = sum(1 for r in rows if r["change_pct"] > 0)
    down = sum(1 for r in rows if r["change_pct"] < 0)
    limit_up = sum(
        1 for r in rows if r["change_pct"] >= (9.6 if r["board"] == "主板" else 19.6)
    )
    with backtest_lock:
        report_snapshot = {sid: backtests.get(sid) for sid in STRATEGY_ORDER}
    strategies = []
    for sid in STRATEGY_ORDER:
        meta = dict(STRATEGIES[sid])
        report = report_snapshot.get(sid)
        meta["win_rate"] = report["win_rate"] if report else None
        meta["backtest_trades"] = (
            report["metrics"]["trades"] if report and report["metrics"] else None
        )
        meta["signal_count"] = sum(1 for s in signals if s["strategy_id"] == sid)
        strategies.append(meta)
    return jsonify(
        {
            "app": "A股短线量化工作站",
            "source": "tencent-live" if LIVE_READY else "demo-simulator",
            "mode": (
                "腾讯/东财真实行情快照"
                if LIVE_READY
                else "离线演示（可加 --live 切换真实行情）"
            ),
            "clock": _market_clock_text(),
            "date": date.today().strftime("%Y-%m-%d"),
            "universe": len(engine.universe),
            "up": up,
            "down": down,
            "flat": len(rows) - up - down,
            "limit_up": limit_up,
            "signal_count": len(signals),
            "quality": {
                "high": sum(1 for s in signals if s["quality"] == "高"),
                "qualified": sum(1 for s in signals if s["quality"] == "合格"),
                "poor": sum(1 for s in signals if s["quality"] == "差"),
            },
            "strength": {
                "strong": sum(1 for s in signals if s["strength"] == "强"),
                "medium": sum(1 for s in signals if s["strength"] == "中"),
                "weak": sum(1 for s in signals if s["strength"] == "弱"),
            },
            "strategies": strategies,
            "backtest_ready": all(
                report_snapshot.get(sid) is not None for sid in STRATEGY_ORDER
            ),
        }
    )


@app.get("/api/market")
def market_overview():
    rows = engine.market_rows()
    rows.sort(key=lambda x: x["change_pct"], reverse=True)
    signals = sorted(
        engine.signals,
        key=lambda s: (-(s["score"] or 0), s["change_pct"]),
    )
    return jsonify(
        {
            "clock": _market_clock_text(),
            "quotes": rows,
            "top_gainers": rows[:10],
            "top_losers": list(reversed(rows[-10:])),
            "signals": signals[:40],
            "watchlist": [engine.quotes[c] for c in watchlist if c in engine.quotes],
        }
    )


@app.get("/api/quotes")
def quotes():
    codes = request.args.get("codes")
    rows = engine.market_rows()
    if codes:
        wanted = {c.strip() for c in codes.split(",") if c.strip()}
        rows = [r for r in rows if r["code"] in wanted]
    sort_key = request.args.get("sort", "change_pct")
    if sort_key in ("change_pct", "volume_ratio", "turnover", "amount", "price"):
        rows.sort(key=lambda r: r.get(sort_key) or 0, reverse=True)
    return jsonify({"rows": rows, "clock": _market_clock_text()})


@app.get("/api/search")
def search():
    query = (request.args.get("q") or "").strip().lower()
    if not query:
        return jsonify([])
    out = []
    for stock in engine.universe:
        haystack = f"{stock['code']} {stock['name']} {stock['sector']}".lower()
        if query in haystack:
            quote = engine.quotes[stock["code"]]
            out.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "sector": stock["sector"],
                    "board": stock["board"],
                    "price": quote["price"],
                    "change_pct": quote["change_pct"],
                }
            )
    out.sort(key=lambda x: x["code"])
    return jsonify(out[:20])


@app.get("/api/screener")
def screener():
    def query_float(name):
        raw = request.args.get(name)
        if raw is None or raw == "":
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    price_min = query_float("price_min")
    price_max = query_float("price_max")
    pct_min = query_float("pct_min")
    pct_max = query_float("pct_max")
    volume_ratio_min = query_float("volume_ratio_min")
    turnover_min = query_float("turnover_min")
    sector = request.args.get("sector", "all")
    board = request.args.get("board", "all")
    strength = request.args.get("strength", "all")
    quality = request.args.get("quality", "all")

    rows = engine.market_rows()
    signal_by_code = {}
    for signal in engine.signals:
        signal_by_code.setdefault(signal["code"], []).append(signal)

    def keep(row):
        if price_min is not None and row["price"] < price_min:
            return False
        if price_max is not None and row["price"] > price_max:
            return False
        if pct_min is not None and row["change_pct"] < pct_min:
            return False
        if pct_max is not None and row["change_pct"] > pct_max:
            return False
        if volume_ratio_min is not None and row["volume_ratio"] < volume_ratio_min:
            return False
        if turnover_min is not None and row["turnover"] < turnover_min:
            return False
        if sector != "all" and row["sector"] != sector:
            return False
        if board != "all" and row["board"] != board:
            return False
        signals = signal_by_code.get(row["code"], [])
        if strength != "all" and not any(s["strength"] == strength for s in signals):
            return False
        if quality != "all" and not any(s["quality"] == quality for s in signals):
            return False
        return True

    matched = [row for row in rows if keep(row)]
    matched.sort(key=lambda row: row["change_pct"], reverse=True)
    return jsonify(
        {
            "count": len(matched),
            "rows": matched,
            "signals": engine.signals,
            "filters": {
                "price_min": price_min,
                "price_max": price_max,
                "pct_min": pct_min,
                "pct_max": pct_max,
                "volume_ratio_min": volume_ratio_min,
                "turnover_min": turnover_min,
                "sector": sector,
                "board": board,
                "strength": strength,
                "quality": quality,
            },
        }
    )


@app.get("/api/stocks/<code>")
def stock_detail(code):
    if code not in engine.stock_index:
        return jsonify({"error": "未找到股票"}), HTTPStatus.NOT_FOUND
    _load_live_daily_bars(code)
    quote = engine.quotes[code]
    stock = engine.stock_index[code]
    indicators = engine.indicator_snapshot(code, 180)
    stock_signals = [s for s in engine.signals if s["code"] == code]
    with backtest_lock:
        strategy_reports = {
            sid: backtests.get(sid) for sid in STRATEGY_ORDER
        }
    history = []
    for sid in STRATEGY_ORDER:
        report = strategy_reports.get(sid)
        if not report:
            continue
        for trade in report["trades"]:
            if trade["code"] == code:
                history.append(
                    {
                        "strategy_id": sid,
                        "strategy_name": STRATEGIES[sid]["name"],
                        "entry_date": trade["entry_date"],
                        "exit_date": trade["exit_date"],
                        "pnl_pct": trade["pnl_pct"],
                        "holding_days": trade["holding_days"],
                    }
                )
                break
    return jsonify(
        {
            "stock": stock,
            "quote": quote,
            "indicators_tail": indicators,
            "signals": stock_signals,
            "history": history[:20],
            "win_rates": {
                sid: (report["win_rate"] if report else None)
                for sid, report in strategy_reports.items()
            },
            "clock": _market_clock_text(),
        }
    )


@app.get("/api/stocks/<code>/kline")
def stock_kline(code):
    if code not in engine.stock_index:
        return jsonify({"error": "未找到股票"}), HTTPStatus.NOT_FOUND
    period = request.args.get("period", "day")
    limit = min(max(int(request.args.get("limit", 180)), 20), 600)
    if period in ("day", "1d", "daily", "week", "1w"):
        if LIVE_READY:
            _load_live_daily_bars(code)
        data = engine.indicator_snapshot(code, limit)
        quote = engine.quotes[code]
        today = {
            "date": date.today().strftime("%Y-%m-%d"),
            "open": quote["open"],
            "high": quote["high"],
            "low": quote["low"],
            "close": quote["price"],
            "volume": quote["volume"],
            "amount": quote["amount"],
            "pct": quote["change_pct"],
            "turnover": quote["turnover"],
            "live": True,
        }
        if not data["bars"] or data["bars"][-1]["date"] != today["date"]:
            data["bars"].append(today)
            data["dates"].append(today["date"])
            for key in (
                "ma5",
                "ma10",
                "ma20",
                "ma60",
                "dif",
                "dea",
                "macd",
                "kdj_k",
                "kdj_d",
                "kdj_j",
                "rsi",
                "boll_upper",
                "boll_mid",
                "boll_low",
                "atr",
                "vol_sma5",
            ):
                data[key].append(None)
        return jsonify(
            {
                **data,
                "period": "day",
                "clock": _market_clock_text(),
                "live": LIVE_READY,
                "source": "eastmoney" if LIVE_READY else "demo",
            }
        )
    if period in ("1m", "5m", "15m", "30m", "60m"):
        if LIVE_READY:
            try:
                live_bars = live_source.fetch_kline(code, period, min(limit, 400))
                if live_bars:
                    live_bars = live_bars[-min(limit, 300) :]
                    closes = [b["close"] for b in live_bars]
                    volumes = [b["volume"] for b in live_bars]
                    return jsonify(
                        {
                            "dates": [b["date"] for b in live_bars],
                            "bars": live_bars,
                            "period": period,
                            "ma5": sma(closes, 5),
                            "ma10": sma(closes, 10),
                            "ma20": sma(closes, 20),
                            "rsi": rsi(closes),
                            "vol_sma5": sma(volumes, 5),
                            "live": True,
                            "replay": False,
                            "source": "eastmoney",
                            "note": "东方财富真实分钟K线",
                        }
                    )
            except Exception:
                pass
        data = engine.minute_snapshot(code, period, min(limit, 300))
        return jsonify(
            {
                **data,
                "clock": _market_clock_text(),
                "replay": True,
                "note": "离线合成分钟回放，接入实时行情源后替换。",
                "live": False,
            }
        )
    return (
        jsonify({"error": "不支持的K线周期"}),
        HTTPStatus.BAD_REQUEST,
    )


@app.get("/api/screen")
def screen():
    strategy_id = request.args.get("strategy", "all")
    rows = engine.signals
    if strategy_id != "all":
        rows = [s for s in rows if s["strategy_id"] == strategy_id]
    rows = sorted(rows, key=lambda s: -(s.get("score") or 0))
    return jsonify({"signals": rows, "strategy": strategy_id})


@app.get("/api/strategies")
def strategies():
    with backtest_lock:
        report_snapshot = {
            sid: (backtests.get(sid) if sid in backtests else None)
            for sid in STRATEGY_ORDER
        }
    result = []
    for sid in STRATEGY_ORDER:
        report = report_snapshot.get(sid)
        item = {
            **STRATEGIES[sid],
            "signals": sorted(
                [s for s in engine.signals if s["strategy_id"] == sid],
                key=lambda s: -(s.get("score") or 0),
            ),
            "win_rate": report["win_rate"] if report else None,
            "metrics": report["metrics"] if report else None,
            "trade_count": report["trade_count"] if report else None,
        }
        result.append(item)
    return jsonify({"strategies": result})


@app.get("/api/backtest/<strategy_id>")
def backtest_result(strategy_id):
    if strategy_id not in STRATEGIES:
        return jsonify({"error": "未知策略"}), HTTPStatus.NOT_FOUND
    with backtest_lock:
        report = backtests.get(strategy_id)
    if report is None:
        report = run_backtest(engine, strategy_id, 1_000_000.0)
        with backtest_lock:
            backtests[strategy_id] = report
    return jsonify(report)


@app.post("/api/backtest/run")
def backtest_run():
    body = request.get_json(force=True, silent=True) or {}
    strategy_id = body.get("strategy", "s1")
    if strategy_id not in STRATEGIES:
        return jsonify({"error": "未知策略"}), HTTPStatus.BAD_REQUEST
    capital = float(body.get("capital", 1_000_000))
    report = run_backtest(engine, strategy_id, capital)
    with backtest_lock:
        backtests[strategy_id] = report
    return jsonify(report)


@app.get("/api/watchlist")
def get_watchlist():
    return jsonify(
        {
            "codes": watchlist,
            "rows": [engine.quotes[c] for c in watchlist if c in engine.quotes],
        }
    )


@app.post("/api/watchlist")
def add_watchlist():
    code = (request.get_json(force=True, silent=True) or {}).get("code")
    if code not in engine.stock_index:
        return jsonify({"error": "股票不存在"}), HTTPStatus.BAD_REQUEST
    if code not in watchlist:
        watchlist.append(code)
    return jsonify({"codes": watchlist})


@app.delete("/api/watchlist")
def remove_watchlist():
    code = (request.get_json(force=True, silent=True) or {}).get("code")
    if code in watchlist:
        watchlist.remove(code)
    return jsonify({"codes": watchlist})


@app.get("/api/paper")
def paper_status():
    return jsonify(
        {
            "cash": round(paper_cash, 2),
            "positions": list(paper_positions.values()),
            "orders": paper_orders[-40:][::-1],
        }
    )


@app.post("/api/paper/orders")
def paper_order():
    global paper_cash, _paper_id
    body = request.get_json(force=True, silent=True) or {}
    code = body.get("code")
    action = body.get("action", "buy")
    if code not in engine.stock_index:
        return jsonify({"error": "股票不存在"}), HTTPStatus.BAD_REQUEST
    quote = engine.quotes[code]
    with _order_lock:
        _paper_id += 1
        order_id = _paper_id
        price = quote["price"]
        if action == "buy":
            notional = float(body.get("amount", 100_000))
            shares = int(notional / (price * 100)) * 100
            if shares < 100 or shares * price > paper_cash:
                return jsonify({"error": "资金不足或金额过小"}), HTTPStatus.BAD_REQUEST
            paper_cash -= shares * price
            pos = paper_positions.get(code)
            if pos:
                total_shares = pos["shares"] + shares
                pos["avg_price"] = (pos["avg_price"] * pos["shares"] + shares * price) / total_shares
                pos["shares"] = total_shares
            else:
                paper_positions[code] = {
                    "code": code,
                    "name": quote["name"],
                    "shares": shares,
                    "avg_price": round(price, 3),
                    "strategy": body.get("strategy", "manual"),
                    "opened_at": _market_clock_text(),
                }
        elif action == "sell":
            pos = paper_positions.get(code)
            if not pos:
                return jsonify({"error": "无持仓"}), HTTPStatus.BAD_REQUEST
            shares = int(body.get("shares", pos["shares"]))
            shares = min(shares, pos["shares"])
            paper_cash += shares * price
            pos["shares"] -= shares
            if pos["shares"] == 0:
                del paper_positions[code]
        else:
            return jsonify({"error": "未知操作"}), HTTPStatus.BAD_REQUEST
        paper_orders.append(
            {
                "id": order_id,
                "code": code,
                "name": quote["name"],
                "action": action,
                "price": price,
                "shares": shares,
                "strategy": body.get("strategy", "manual"),
                "time": _market_clock_text(),
            }
        )
    return paper_status()


@app.get("/api/stream")
def stream():
    def generate():
        last_version = engine.signal_version
        while True:
            rows = engine.market_rows()
            payload = {
                "clock": _market_clock_text(),
                "tick": engine.tick,
                "quotes": rows,
                "signals": engine.signals,
                "signal_version": engine.signal_version,
                "signal_event": engine.signal_version != last_version,
            }
            last_version = engine.signal_version
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(3)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--live", action="store_true", help="use Tencent/Eastmoney real quotes")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
