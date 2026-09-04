(function () {
  "use strict";

  const RED = "#d64545";
  const GREEN = "#0f9d6b";
  const GRID = "#e7ebf1";
  const MUTED = "#7b8798";
  const MA_COLORS = { ma5: "#e07b39", ma10: "#3e7bd6", ma20: "#a55eea", ma60: "#3ba55d" };

  function round2(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "--";
    return Number(v).toFixed(2);
  }

  function formatVolume(v) {
    if (v === null || v === undefined) return "--";
    if (v >= 1e8) return (v / 1e8).toFixed(2) + "亿";
    if (v >= 1e4) return (v / 1e4).toFixed(1) + "万";
    return String(v);
  }

  function cssColor(index) {
    return ["#d64545", "#3e7bd6", "#a55eea", "#d99b1f", "#0f9d6b", "#e07b39"][index % 6];
  }

  class KlineChart {
    constructor(canvas, tooltipEl) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.tooltipEl = tooltipEl;
      this.data = null;
      this.overlay = "ma";
      this.hoverIndex = -1;
      this._onMove = (e) => this._handleMove(e);
      this._onLeave = () => this._hideTooltip();
      this._onResize = () => this.draw();
      this.canvas.addEventListener("mousemove", this._onMove);
      this.canvas.addEventListener("mouseleave", this._onLeave);
      window.addEventListener("resize", this._onResize);
    }

    setData(data) {
      this.data = data;
      this.hoverIndex = -1;
      this.draw();
    }

    setOverlay(name) {
      this.overlay = name || "ma";
      this.draw();
    }

    destroy() {
      this.canvas.removeEventListener("mousemove", this._onMove);
      this.canvas.removeEventListener("mouseleave", this._onLeave);
      window.removeEventListener("resize", this._onResize);
    }

    _size() {
      const rect = this.canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.cssW = Math.max(rect.width, 240);
      this.cssH = Math.max(rect.height, 300);
      this.canvas.width = Math.round(this.cssW * dpr);
      this.canvas.height = Math.round(this.cssH * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    draw() {
      if (!this.data || !this.data.bars || !this.data.bars.length) return;
      this._size();
      const ctx = this.ctx;
      const W = this.cssW;
      const H = this.cssH;
      ctx.clearRect(0, 0, W, H);
      ctx.font = "10px 'Segoe UI', sans-serif";
      ctx.textBaseline = "middle";

      const bars = this.data.bars;
      const n = bars.length;
      const left = 62;
      const right = 16;
      const top = 12;
      const bottom = 22;
      const volumeH = Math.min(72, Math.max(42, H * 0.13));
      const hasIndicator = ["macd", "kdj", "rsi"].indexOf(this.overlay) >= 0;
      const indicatorH = hasIndicator ? Math.max(84, H * 0.16) : 0;
      const gap = hasIndicator ? 14 : 10;
      const mainH = H - top - bottom - volumeH - indicatorH - gap * 1.7;
      const plotW = W - left - right;
      const step = plotW / n;
      const candleW = Math.max(1, step * 0.68);
      const candleTop = top;
      const volumeTop = candleTop + mainH + 10;
      const indicatorTop = volumeTop + volumeH + gap - 8;

      const closes = bars.map((b) => b.close);
      let min = Math.min.apply(null, bars.map((b) => b.low));
      let max = Math.max.apply(null, bars.map((b) => b.high));
      const overlayKeys = [];
      if (this.overlay === "ma") overlayKeys.push("ma5", "ma10", "ma20", "ma60");
      if (this.overlay === "boll") overlayKeys.push("boll_upper", "boll_mid", "boll_low");
      overlayKeys.forEach((key) => {
        const arr = (this.data[key] || []).filter((x) => x !== null && x !== undefined);
        if (!arr.length) return;
        const a = Math.min.apply(null, arr);
        const b = Math.max.apply(null, arr);
        if (a < min) min = a;
        if (b > max) max = b;
      });
      const pad = (max - min) * 0.05 || Math.max(max * 0.01, 0.1);
      min -= pad;
      max += pad;

      const yPrice = (price) => candleTop + ((max - price) / (max - min)) * mainH;
      const x = (i) => left + i * step + step / 2;

      ctx.strokeStyle = GRID;
      ctx.fillStyle = MUTED;
      for (let g = 0; g <= 5; g++) {
        const gy = candleTop + (mainH * g) / 5;
        ctx.beginPath();
        ctx.moveTo(left, gy);
        ctx.lineTo(W - right, gy);
        ctx.stroke();
        const val = max - ((max - min) * g) / 5;
        ctx.fillText(val.toFixed(2), 4, gy);
      }

      const labelEvery = Math.max(1, Math.ceil(n / 9));
      ctx.fillStyle = MUTED;
      for (let i = 0; i < n; i++) {
        if (i % labelEvery === 0 || i === n - 1) {
          const label = (this.data.dates[i] || "").slice(5);
          ctx.fillText(label, x(i) - 16, H - 10);
        }
        if (i % 3 === 0) {
          ctx.strokeStyle = "#f0f2f6";
          ctx.beginPath();
          ctx.moveTo(x(i), candleTop);
          ctx.lineTo(x(i), candleTop + mainH);
          ctx.stroke();
          ctx.strokeStyle = GRID;
        }
      }

      ctx.textAlign = "right";
      for (let i = 0; i < n; i++) {
        const bar = bars[i];
        const isUp = bar.close >= bar.open;
        const color = isUp ? RED : GREEN;
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        const hiY = yPrice(bar.high);
        const loY = yPrice(bar.low);
        ctx.beginPath();
        ctx.moveTo(x(i), hiY);
        ctx.lineTo(x(i), loY);
        ctx.stroke();
        const openY = yPrice(bar.open);
        const closeY = yPrice(bar.close);
        const bodyTop = Math.min(openY, closeY);
        const bodyH = Math.max(Math.abs(openY - closeY), 1);
        ctx.fillRect(x(i) - candleW / 2, bodyTop, candleW, bodyH);

        const volMax = Math.max.apply(null, bars.map((b) => b.volume || 0)) || 1;
        const volH = (volumeH - 12) * ((bar.volume || 0) / volMax);
        ctx.globalAlpha = 0.78;
        ctx.fillRect(x(i) - candleW / 2, volumeTop + volumeH - 4 - volH, candleW, Math.max(1, volH));
        ctx.globalAlpha = 1;
      }

      ctx.textAlign = "left";
      const lineKeyDefs = {
        ma5: [this.data.ma5, MA_COLORS.ma5],
        ma10: [this.data.ma10, MA_COLORS.ma10],
        ma20: [this.data.ma20, MA_COLORS.ma20],
        ma60: [this.data.ma60, MA_COLORS.ma60],
        boll_upper: [this.data.boll_upper, "#d64545"],
        boll_mid: [this.data.boll_mid, "#d99b1f"],
        boll_low: [this.data.boll_low, "#0f9d6b"],
      };
      overlayKeys.forEach((key, ki) => {
        const [arr, color] = lineKeyDefs[key] || [];
        if (!arr) return;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        let started = false;
        arr.forEach((value, i) => {
          if (value === null || value === undefined || !Number.isFinite(value)) return;
          const px = x(i);
          const py = yPrice(value);
          if (!started) {
            ctx.moveTo(px, py);
            started = true;
          } else {
            ctx.lineTo(px, py);
          }
        });
        ctx.stroke();
        if (started) {
          ctx.fillStyle = color;
          ctx.fillText(key.toUpperCase(), left + 4 + ki * 46, candleTop + 10);
        }
      });
      ctx.lineWidth = 1;

      if (hasIndicator) this._drawIndicator(volumeTop + volumeH, indicatorH, bars, left, W - right);

      this._drawCrosshair();
    }

    _drawIndicator(y, h, bars, left, rightX) {
      const ctx = this.ctx;
      const W = this.cssW;
      ctx.strokeStyle = GRID;
      ctx.fillStyle = MUTED;
      for (let g = 0; g <= 2; g++) {
        const gy = y + (h * g) / 2;
        ctx.beginPath();
        ctx.moveTo(left, gy);
        ctx.lineTo(rightX, gy);
        ctx.stroke();
      }
      const n = bars.length;
      const step = (rightX - left) / n;
      const x = (i) => left + i * step + step / 2;
      const label = this.overlay.toUpperCase();
      ctx.fillStyle = MUTED;
      ctx.fillText(label, left + 5, y + 10);

      if (this.overlay === "macd") {
        const hist = this.data.macd || [];
        const dif = this.data.dif || [];
        const dea = this.data.dea || [];
        const values = hist.concat(dif, dea).filter((v) => v !== null && v !== undefined);
        let maxAbs = 1;
        values.forEach((v) => {
          if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v);
        });
        const toY = (v) => y + h / 2 - (v / maxAbs) * (h / 2 - 8);
        ctx.strokeStyle = GRID;
        ctx.beginPath();
        ctx.moveTo(left, y + h / 2);
        ctx.lineTo(rightX, y + h / 2);
        ctx.stroke();
        hist.forEach((v, i) => {
          if (v === null || v === undefined) return;
          ctx.fillStyle = v >= 0 ? RED : GREEN;
          const barW = Math.max(1, step * 0.55);
          if (v >= 0) ctx.fillRect(x(i) - barW / 2, toY(v), barW, y + h / 2 - toY(v));
          else ctx.fillRect(x(i) - barW / 2, y + h / 2, barW, toY(v) - (y + h / 2));
        });
        this._line(dif, x, toY, "#e07b39");
        this._line(dea, x, toY, "#3e7bd6");
      } else {
        const seriesKeys = this.overlay === "kdj" ? ["kdj_k", "kdj_d", "kdj_j"] : ["rsi"];
        const colors = ["#3e7bd6", "#d99b1f", "#a55eea"];
        const fixedMin = this.overlay === "rsi" ? 0 : 0;
        const fixedMax = this.overlay === "rsi" ? 100 : 100;
        const toY = (v) => y + ((fixedMax - v) / (fixedMax - fixedMin)) * (h - 16) + 8;
        seriesKeys.forEach((key, idx) => {
          this._line(this.data[key] || [], x, toY, colors[idx]);
        });
      }
    }

    _line(arr, xFn, yFn, color) {
      const ctx = this.ctx;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      let started = false;
      arr.forEach((value, i) => {
        if (value === null || value === undefined || !Number.isFinite(value)) return;
        const px = xFn(i);
        const py = yFn(value);
        if (!started) {
          ctx.moveTo(px, py);
          started = true;
        } else {
          ctx.lineTo(px, py);
        }
      });
      ctx.stroke();
      ctx.lineWidth = 1;
    }

    _drawCrosshair() {
      if (this.hoverIndex < 0 || !this.data) return;
      const ctx = this.ctx;
      const bars = this.data.bars;
      const n = bars.length;
      if (this.hoverIndex >= n) this.hoverIndex = n - 1;
      const left = 62;
      const right = this.cssW - 16;
      const plotW = right - left;
      const step = plotW / n;
      const cx = left + this.hoverIndex * step + step / 2;
      const top = 12;
      const bottomH = this.cssH - 22;
      ctx.strokeStyle = "rgba(60,70,90,0.45)";
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(cx, top);
      ctx.lineTo(cx, bottomH);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    _handleMove(e) {
      if (!this.data || !this.data.bars.length) return;
      const rect = this.canvas.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const left = 62;
      const right = rect.width - 16;
      const plotW = right - left;
      const step = plotW / this.data.bars.length;
      let idx = Math.floor((px - left) / step);
      idx = Math.max(0, Math.min(this.data.bars.length - 1, idx));
      if (idx !== this.hoverIndex) {
        this.hoverIndex = idx;
        this.draw();
      }
      const bar = this.data.bars[idx];
      const date = this.data.dates[idx];
      const pct = bar.pct !== undefined ? bar.pct : ((bar.close / bar.open - 1) * 100);
      const sign = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
      const rows = [
        ["时间", date],
        ["开盘", round2(bar.open)],
        ["最高", round2(bar.high)],
        ["最低", round2(bar.low)],
        ["收盘", round2(bar.close)],
        ["涨跌幅", (pct >= 0 ? "+" : "") + Number(pct).toFixed(2) + "%"],
        ["成交量", formatVolume(bar.volume)],
      ];
      if (this.data.ma5 && this.data.ma5[idx] !== null && this.data.ma5[idx] !== undefined) {
        rows.push(["MA5", round2(this.data.ma5[idx])]);
      }
      if (this.data.rsi && this.data.rsi[idx] !== null && this.data.rsi[idx] !== undefined) {
        rows.push(["RSI14", round2(this.data.rsi[idx])]);
      }
      this.tooltipEl.innerHTML = rows
        .map(
          (r) =>
            `<div class="row"><span>${r[0]}</span><strong class="${r[0] === "涨跌幅" ? sign : ""}">${r[1]}</strong></div>`
        )
        .join("");
      this.tooltipEl.classList.remove("hidden");
      const tooltipW = Math.min(220, this.cssW - cx - 20);
      const leftPos = cx + 12 < this.cssW - 200 ? cx + 12 : Math.max(4, cx - tooltipW - 14);
      this.tooltipEl.style.left = leftPos + "px";
      this.tooltipEl.style.top = "18px";
    }

    _hideTooltip() {
      this.hoverIndex = -1;
      if (this.tooltipEl) this.tooltipEl.classList.add("hidden");
      this.draw();
    }
  }

  class LineChart {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.data = [];
      this._resize = () => this.draw();
      window.addEventListener("resize", this._resize);
    }

    setData(points) {
      this.data = points || [];
      this.draw();
    }

    destroy() {
      window.removeEventListener("resize", this._resize);
    }

    draw() {
      const canvas = this.canvas;
      const ctx = this.ctx;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const W = Math.max(rect.width, 240);
      const H = Math.max(rect.height, 280);
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      if (!this.data.length) {
        ctx.fillStyle = MUTED;
        ctx.textAlign = "center";
        ctx.fillText("暂无回测结果", W / 2, H / 2);
        return;
      }
      const left = 64;
      const right = 16;
      const top = 18;
      const bottom = 28;
      const values = this.data.map((d) => d.equity);
      const min = Math.min.apply(null, values);
      const max = Math.max.apply(null, values);
      const pad = (max - min) * 0.08 || Math.max(max * 0.01, 1);
      const y0 = top;
      const y1 = H - bottom;
      const plotW = W - left - right;
      const x = (i) => left + (plotW * i) / Math.max(1, this.data.length - 1);
      const y = (v) => y1 - ((v - (min - pad)) / (max + pad - (min - pad))) * (y1 - y0);
      ctx.font = "10px sans-serif";
      ctx.fillStyle = MUTED;
      ctx.strokeStyle = GRID;
      for (let g = 0; g <= 4; g++) {
        const gy = y0 + ((y1 - y0) * g) / 4;
        ctx.beginPath();
        ctx.moveTo(left, gy);
        ctx.lineTo(W - right, gy);
        ctx.stroke();
        const value = max + pad - ((max + pad - (min - pad)) * g) / 4;
        ctx.fillText(value.toFixed(0), 4, gy);
      }
      const step = Math.ceil(this.data.length / 8);
      for (let i = 0; i < this.data.length; i += step) {
        ctx.fillText(this.data[i].date || "", x(i) - 20, H - 10);
      }
      ctx.strokeStyle = "#3e7bd6";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      this.data.forEach((d, i) => {
        if (i === 0) ctx.moveTo(x(i), y(d.equity));
        else ctx.lineTo(x(i), y(d.equity));
      });
      ctx.stroke();
      ctx.fillStyle = "#3e7bd6";
      this.data.forEach((d, i) => {
        if (i % Math.ceil(this.data.length / 120) === 0) {
          ctx.beginPath();
          ctx.arc(x(i), y(d.equity), 1.6, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }
  }

  window.KlineChart = KlineChart;
  window.LineChart = LineChart;
})();
