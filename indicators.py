"""Technical indicator helpers used by screens and charts.

Functions accept arrays and return arrays aligned with the input. Values before
enough lookback data are None.
"""


def sma(values, period):
    out = [None] * len(values)
    if not values:
        return out
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = round(running / period, 4)
    return out


def ema(values, period):
    out = [None] * len(values)
    if not values:
        return out
    alpha = 2.0 / (period + 1.0)
    prev = values[0]
    for i, value in enumerate(values):
        if i == 0:
            out[i] = value
            continue
        prev = value * alpha + prev * (1 - alpha)
        out[i] = round(prev, 4)
    return out


def macd(closes, fast=12, slow=26, signal=9):
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = []
    for a, b in zip(ema_fast, ema_slow):
        if a is None or b is None:
            dif.append(None)
        else:
            dif.append(round(a - b, 4))
    dea = ema([0 if x is None else x for x in dif], signal)
    dea = [None if d is None else round(d, 4) for d in dea]
    hist = []
    for d, e in zip(dif, dea):
        if d is None or e is None:
            hist.append(None)
        else:
            hist.append(round((d - e) * 2, 4))
    return dif, dea, hist


def rsi(closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period, len(closes)):
        if i > period:
            delta = closes[i] - closes[i - 1]
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = round(100 - 100 / (1 + rs), 2)
    return out


def kdj(highs, lows, closes, period=9):
    k_values = [None] * len(closes)
    d_values = [None] * len(closes)
    j_values = [None] * len(closes)
    if not closes:
        return k_values, d_values, j_values
    k = 50.0
    d = 50.0
    for i in range(len(closes)):
        start = max(0, i - period + 1)
        window_high = max(highs[start : i + 1])
        window_low = min(lows[start : i + 1])
        if window_high == window_low:
            rsv = 50.0
        else:
            rsv = (closes[i] - window_low) / (window_high - window_low) * 100
        k = (2.0 / 3.0) * k + (1.0 / 3.0) * rsv
        d = (2.0 / 3.0) * d + (1.0 / 3.0) * k
        j = 3 * k - 2 * d
        k_values[i] = round(k, 2)
        d_values[i] = round(d, 2)
        j_values[i] = round(j, 2)
    return k_values, d_values, j_values


def boll(closes, period=20, multiplier=2.0):
    upper = [None] * len(closes)
    middle = sma(closes, period)
    lower = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5
        mid = mean
        upper[i] = round(mid + multiplier * std, 4)
        middle[i] = round(mid, 4)
        lower[i] = round(mid - multiplier * std, 4)
    return upper, middle, lower


def atr(highs, lows, closes, period=14):
    trs = [None] * len(closes)
    out = [None] * len(closes)
    for i in range(1, len(closes)):
        trs[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    if len(closes) <= period:
        return out
    prev_atr = sum(x for x in trs[1 : period + 1]) / period
    out[period] = round(prev_atr, 4)
    for i in range(period + 1, len(closes)):
        prev_atr = (prev_atr * (period - 1) + trs[i]) / period
        out[i] = round(prev_atr, 4)
    return out


def rolling_gain(closes, period):
    out = [None] * len(closes)
    for i in range(period, len(closes)):
        prev = closes[i - period]
        if prev:
            out[i] = closes[i] / prev - 1
    return out
