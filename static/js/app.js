(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const state = {
    view: "dashboard",
    quotes: [],
    signals: [],
    meta: null,
    market: null,
    watchlistCodes: [],
    strategies: null,
    activeStrategy: "s1",
    marketTab: "all",
    quality: "all",
    stockCode: null,
    stockToken: 0,
    period: "day",
    overlay: "ma",
    paper: null,
    chartData: null,
    backtest: null,
    searchTimer: null,
    lastSignalKeys: new Set(),
    screenerTimer: null,
  };

  const iconPaths = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect>',
    zap: '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"></path>',
    chart: '<path d="M3 3v18h18"></path><path d="m7 14 4-4 3 3 5-6"></path>',
    wallet: '<path d="M21 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h15a2 2 0 0 0 2-2v-2"></path><path d="M17 12h4v4h-4a2 2 0 0 1 0-4Z"></path>',
    arrow: '<path d="m15 18-6-6 6-6"></path>',
    plus: '<path d="M12 5v14M5 12h14"></path>',
    star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2Z"></path>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.7 21a2 2 0 0 1-3.4 0"></path>',
    activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>',
    play: '<path d="m6 3 14 9-14 9V3Z"></path>',
    refresh: '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"></path><path d="M21 3v5h-5"></path><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"></path><path d="M3 21v-5h5"></path>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14a9 3 0 0 0 18 0V5"></path><path d="M3 12a9 3 0 0 0 18 0"></path>',
  };

  function icon(name) {
    return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.grid}</svg>`;
  }

  function esc(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function num(v, digits) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "--";
    return n.toFixed(digits === undefined ? 2 : digits);
  }

  function signed(v, digits) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "--";
    return (n > 0 ? "+" : "") + n.toFixed(digits === undefined ? 2 : digits);
  }

  function pctClass(v) {
    const n = Number(v);
    return n > 0 ? "up" : n < 0 ? "down" : "flat";
  }

  function fmtAmount(v) {
    const n = Number(v);
    if (!Number.isFinite(n) || !n) return "--";
    if (n >= 1e8) return (n / 1e8).toFixed(2) + "亿";
    if (n >= 1e4) return (n / 1e4).toFixed(1) + "万";
    return n.toFixed(0);
  }

  async function api(path, options) {
    const opts = options || {};
    const init = { headers: { "Content-Type": "application/json" } };
    if (opts.method) init.method = opts.method;
    if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
    const res = await fetch(path, init);
    if (!res.ok) {
      let message = "请求失败";
      try {
        const data = await res.json();
        message = data.error || message;
      } catch (err) {
        message = res.statusText || message;
      }
      throw new Error(message);
    }
    return res.json();
  }

  function toast(title, text) {
    const el = document.createElement("div");
    el.className = "toast";
    el.innerHTML = `<div class="t-title">${esc(title)}</div><div>${esc(text || "")}</div>`;
    $("#toastRegion").appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }

  function stockCell(stock, code, sector) {
    return `<div class="stock-cell"><div><div class="name">${esc(stock)}</div><div class="code">${esc(code)} · ${esc(sector || "")}</div></div></div>`;
  }

  function qualityBadge(value) {
    const cls = value === "高" ? "high" : value === "合格" ? "qualified" : "poor";
    return `<span class="badge ${cls}">${esc(value)}</span>`;
  }

  function strengthBadge(value) {
    const cls = value === "强" ? "strong" : value === "中" ? "medium" : "weak";
    return `<span class="badge ${cls}">${esc(value)}</span>`;
  }

  function signalRows(rows) {
    if (!rows || !rows.length) return `<div class="empty-state">暂无信号</div>`;
    return `<table class="data-table"><thead><tr>
      <th>策略</th><th>股票</th><th>现价</th><th>涨跌</th><th>量比</th>
      <th>强度</th><th>质量</th><th>评分</th><th>建议</th></tr></thead><tbody>
      ${rows
        .map(
          (s) => `<tr class="stock-row" data-open-stock="${esc(s.code)}">
            <td><strong>${esc(s.strategy_name)}</strong><div class="code">${esc(s.window || "")}</div></td>
            <td>${stockCell(s.name, s.code, s.sector)}</td>
            <td class="num">${num(s.price)}</td>
            <td class="num ${pctClass(s.change_pct)}">${signed(s.change_pct)}%</td>
            <td class="num">${num(s.volume_ratio)}</td>
            <td>${strengthBadge(s.strength)}</td>
            <td>${qualityBadge(s.quality)}</td>
            <td class="num score-chip ${pctClass(Number(s.score) - 60)}">${num(s.score, 0)}</td>
            <td><span class="muted">${esc(s.action)}</span></td></tr>`
        )
        .join("")}
    </tbody></table>`;
  }

  // ---------- navigation and routing ----------
  const NAV = [
    ["dashboard", "市场雷达", "grid"],
    ["strategies", "策略工作台", "zap"],
    ["backtest", "回测中心", "chart"],
    ["paper", "自选模拟", "wallet"],
  ];

  function renderNav() {
    $("#mainNav").innerHTML = NAV.map(
      ([view, label, iconName]) =>
        `<button class="nav-item" data-nav="${view}" type="button">${icon(iconName)}<span>${label}</span></button>`
    ).join("");
  }

  function clockText(value) {
    $("#clockText").textContent = value || "--:--";
    $("#livePill").title = "离线演示盘中回放，接入免费行情源后可切换为真实快照";
  }

  function route() {
    const hash = location.hash || "#/";
    let view = "dashboard";
    let code = null;
    const stockMatch = hash.match(/^#\/stock\/([0-9]{6})/);
    if (stockMatch) {
      view = "stock";
      code = stockMatch[1];
    } else if (hash.startsWith("#/strategies")) view = "strategies";
    else if (hash.startsWith("#/backtest")) view = "backtest";
    else if (hash.startsWith("#/paper")) view = "paper";
    state.view = view;
    $$(".view").forEach((el) => el.classList.add("hidden"));
    $(`#view-${view}`).classList.remove("hidden");
    $$(".nav-item").forEach((el) =>
      el.classList.toggle("active", el.dataset.nav === view)
    );
    if (view === "dashboard") loadDashboard();
    else if (view === "strategies") loadStrategiesView();
    else if (view === "stock" && code) loadStock(code);
    else if (view === "backtest") loadBacktestView();
    else if (view === "paper") loadPaperView();
    else if (view === "dashboard") loadDashboard();
  }

  function openStock(code) {
    if (!code) return;
    location.hash = `#/stock/${code}`;
  }

  // ---------- dashboard ----------
  async function loadDashboard() {
    try {
      const [meta, market] = await Promise.all([api("/api/meta"), api("/api/market")]);
      state.meta = meta;
      state.market = market;
      state.quotes = market.quotes || [];
      state.signals = market.signals || [];
      renderDashboard(meta, market);
    } catch (err) {
      toast("市场雷达加载失败", err.message);
    }
  }

  function renderDashboard(meta, market) {
    $("#marketSubtitle").textContent = `${meta.date || ""} · 模拟盘中 ${meta.clock || "--:--"} · ${meta.universe || 0} 只样本股票`;
    $("#sourceTag").textContent = meta.mode || "离线演示";
    clockText(meta.clock);
    $("#metricStrip").innerHTML = [
      ["上涨 / 下跌", `${meta.up || 0} / ${meta.down || 0}`, "red", `${meta.flat || 0} 平盘`, "上涨下跌家数"],
      ["涨停家数", meta.limit_up || 0, "red", "含 10cm / 20cm 口径", "涨停监控"],
      ["当前信号", meta.signal_count || 0, "amber", `强 ${meta.strength?.strong || 0} · 中 ${meta.strength?.medium || 0} · 弱 ${meta.strength?.weak || 0}`, "策略信号"],
      ["质量分布", `${meta.quality?.high || 0} 高`, "green", `合格 ${meta.quality?.qualified || 0} · 差 ${meta.quality?.poor || 0}`, "质量分级"],
      ["策略胜率", meta.backtest_ready ? "已就绪" : "预热中", "blue", "每策略独立回测口径", "历史回测"],
      ["数据源", "离线模拟", "blue", "3 秒推流 · 全池 30 秒扫描", "准实时"],
    ]
      .map(
        ([label, value, color, hint, extra]) =>
          `<div class="metric"><span class="label">${esc(label)}</span><span class="value" style="color:${color === "red" ? "#d64545" : color === "green" ? "#0f9d6b" : color === "amber" ? "#d99b1f" : "#202632"}">${value}</span><span class="hint">${esc(hint)}</span></div>`
      )
      .join("");
    $("#signalTable").innerHTML = signalRows((market.signals || []).slice(0, 30));
    fillScreenerSectors();
    renderMarketTable(market);
  }

  function marketRowsForTab() {
    const rows = screenerRows();
    if (state.marketTab === "watch") {
      const wanted = new Set(state.watchlistCodes);
      return rows.filter((r) => wanted.has(r.code));
    }
    if (state.marketTab === "gainers") {
      return [...rows].sort((a, b) => b.change_pct - a.change_pct).slice(0, 40);
    }
    if (state.marketTab === "volume") {
      return [...rows].sort((a, b) => b.volume_ratio - a.volume_ratio).slice(0, 40);
    }
    return [...rows].sort(
      (a, b) =>
        (b.signal_count || 0) - (a.signal_count || 0) ||
        b.change_pct - a.change_pct
    );
  }

  function fillScreenerSectors() {
    const select = $("#filterSector");
    if (!select || select.options.length > 1) return;
    const sectors = Array.from(new Set((state.quotes || []).map((r) => r.sector).filter(Boolean))).sort();
    select.innerHTML =
      '<option value="all">全部行业</option>' +
      sectors.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("");
  }

  function readNumber(id) {
    const raw = $(id) ? $(id).value : "";
    if (raw === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  function screenerRows() {
    const all = state.quotes || [];
    const priceMin = readNumber("#filterPriceMin");
    const priceMax = readNumber("#filterPriceMax");
    const pctMin = readNumber("#filterPctMin");
    const pctMax = readNumber("#filterPctMax");
    const volMin = readNumber("#filterVolMin");
    const turnMin = readNumber("#filterTurnMin");
    const sector = $("#filterSector") ? $("#filterSector").value : "all";
    const board = $("#filterBoard") ? $("#filterBoard").value : "all";
    const strength = $("#filterStrength") ? $("#filterStrength").value : "all";
    const quality = $("#filterQuality") ? $("#filterQuality").value : "all";
    const signalByCode = {};
    (state.signals || []).forEach((s) => {
      signalByCode[s.code] = signalByCode[s.code] || [];
      signalByCode[s.code].push(s);
    });
    return all.filter((r) => {
      if (priceMin !== null && r.price < priceMin) return false;
      if (priceMax !== null && r.price > priceMax) return false;
      if (pctMin !== null && r.change_pct < pctMin) return false;
      if (pctMax !== null && r.change_pct > pctMax) return false;
      if (volMin !== null && (r.volume_ratio || 0) < volMin) return false;
      if (turnMin !== null && (r.turnover || 0) < turnMin) return false;
      if (sector !== "all" && r.sector !== sector) return false;
      if (board !== "all" && r.board !== board) return false;
      const codes = signalByCode[r.code] || [];
      if (strength !== "all" && !codes.some((s) => s.strength === strength)) return false;
      if (quality !== "all" && !codes.some((s) => s.quality === quality)) return false;
      return true;
    });
  }

  function renderMarketTable(market) {
    if (market) state.market = market;
    const rows = marketRowsForTab();
    const countEl = $("#marketCount");
    if (countEl) countEl.textContent = rows.length ? `${rows.length} 只` : "";
    if (!rows.length) {
      $("#marketTable").innerHTML = `<div class="empty-state">没有匹配当前条件的股票</div>`;
      return;
    }
    $("#marketTable").innerHTML = `<table class="data-table"><thead><tr>
      <th>股票</th><th>行业</th><th>现价</th><th>涨跌</th><th>量比</th><th>换手</th><th>成交额</th><th>信号</th></tr></thead><tbody>
      ${rows
        .map(
          (r) => `<tr class="stock-row" data-open-stock="${esc(r.code)}">
            <td>${stockCell(r.name, r.code, r.board)}</td>
            <td>${esc(r.sector || "")}</td>
            <td class="num">${num(r.price)}</td>
            <td class="num ${pctClass(r.change_pct)}">${signed(r.change_pct)}%</td>
            <td class="num">${num(r.volume_ratio)}</td>
            <td class="num">${num(r.turnover)}%</td>
            <td class="num">${fmtAmount(r.amount)}</td>
            <td>${r.signal_count ? `<span class="pill ${r.signal_count > 1 ? "up" : "flat"}">${r.signal_count}</span>` : ""}</td></tr>`
        )
        .join("")}
    </tbody></table>`;
  }

  // ---------- strategies ----------
  async function loadStrategiesView() {
    try {
      if (!state.strategies) {
        const data = await api("/api/strategies");
        state.strategies = data.strategies;
      }
      if (!state.strategies.some((s) => s.id === state.activeStrategy)) {
        state.activeStrategy = state.strategies[0].id;
      }
      renderStrategySidebar();
      renderStrategyRules();
      renderStrategySignals();
    } catch (err) {
      toast("策略工作台加载失败", err.message);
    }
  }

  function currentStrategyMeta() {
    return (state.strategies || []).find((s) => s.id === state.activeStrategy) || null;
  }

  function strategySignalsFor(s) {
    const priceMin = readNumber("#strategyPriceMin");
    const priceMax = readNumber("#strategyPriceMax");
    return (s.signals || []).filter(
      (sig) =>
        (state.quality === "all" || sig.quality === state.quality) &&
        (priceMin === null || sig.price >= priceMin) &&
        (priceMax === null || sig.price <= priceMax)
    );
  }

  function renderStrategySidebar() {
    $("#strategyNav").innerHTML = (state.strategies || [])
      .map((s) => {
        const win = s.win_rate === null || s.win_rate === undefined ? "--" : num(s.win_rate, 1) + "%";
        return `<button class="strategy-card ${s.id === state.activeStrategy ? "active" : ""}" data-strategy="${s.id}" type="button">
          <div class="row"><span class="name">${esc(s.name)}</span><span class="win ${s.win_rate === null || s.win_rate === undefined ? "warm" : ""}">${win}</span></div>
          <div class="sub">${esc(s.tag)} · 回测 ${s.trade_count === null || s.trade_count === undefined ? "预热中" : `${s.trade_count} 笔`}</div>
          <div class="tags"><span>${esc(s.window)}</span><span>${esc(s.risk)}风险</span></div>
        </button>`;
      })
      .join("");
  }

  function renderStrategyRules() {
    const s = currentStrategyMeta();
    if (!s) return;
    const signals = strategySignalsFor(s);
    $("#strategyRules").innerHTML = `<div class="rule-block">
      <div class="rule-head"><h2>${esc(s.name)}</h2><div class="heading-actions">
        <span class="chip">${esc(s.tag)}</span>
        <span class="chip ${s.risk === "高" || s.risk === "中高" ? "hot" : ""}">${esc(s.risk)}风险</span>
        <span class="chip">窗口 ${esc(s.window)}</span></div></div>
      <p class="muted">${esc(s.objective)}</p>
      <div class="rule-grid">
        <div class="rule-item"><h4>股票筛选</h4><ul>${(s.screen_conditions || []).map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>
        <div class="rule-item"><h4>买入操作</h4><p>${esc(s.buy_rule)}</p></div>
        <div class="rule-item"><h4>卖出与风控</h4><p>${esc(s.sell_rule)}</p></div>
        <div class="rule-item"><h4>当前结果</h4>
          <div class="rule-actions">
            <span class="chip">胜率 ${s.win_rate === null || s.win_rate === undefined ? "预热中" : num(s.win_rate, 1) + "%"}</span>
            <span class="chip">信号 ${signals.length}</span>
            <span class="chip">回测笔数 ${s.trade_count || 0}</span>
            <button class="btn btn-ghost btn-sm" data-goto-backtest="${s.id}" type="button">${icon("play")}查看回测</button>
          </div>
        </div>
      </div>
    </div>`;
    $("#strategySignals").innerHTML = signalRows(signals.slice(0, 40));
  }

  function renderStrategySignals() {
    const s = currentStrategyMeta();
    if (!s) return;
    const signals = strategySignalsFor(s);
    const countEl = $("#strategyPriceCount");
    if (countEl) countEl.textContent = `当前 ${signals.length} 条信号`;
    $("#strategySignals").innerHTML = signalRows(signals.slice(0, 40));
  }

  // ---------- stock detail ----------
  const klineChart = new window.KlineChart($("#klineCanvas"), $("#chartTooltip"));

  async function loadStock(code) {
    state.stockCode = code;
    state.period = "day";
    state.overlay = "ma";
    const token = ++state.stockToken;
    $("#chartSummary").textContent = "K线载入中…";
    $("#detailSignals").innerHTML = `<div class="empty-state">信号载入中…</div>`;
    try {
      const [watch] = await Promise.all([api("/api/watchlist")]);
      state.watchlistCodes = watch.codes;
      const detail = await api(`/api/stocks/${code}`);
      const kline = await api(`/api/stocks/${code}/kline?period=day&limit=180`);
      if (token !== state.stockToken) return;
      state.stockCode = code;
      state.chartData = { detail, kline };
      renderStockDetail(detail);
      applyChartData(kline);
    } catch (err) {
      if (token === state.stockToken) toast("个股详情加载失败", err.message);
    }
  }

  async function reloadStockKline() {
    if (!state.stockCode) return;
    try {
      const kline = await api(
        `/api/stocks/${state.stockCode}/kline?period=${state.period}&limit=240`
      );
      state.chartData.kline = kline;
      applyChartData(kline);
    } catch (err) {
      toast("K线加载失败", err.message);
    }
  }

  function lastValue(arr) {
    if (!arr) return null;
    for (let i = arr.length - 1; i >= 0; i--) {
      if (arr[i] !== null && arr[i] !== undefined && Number.isFinite(arr[i])) return arr[i];
    }
    return null;
  }

  function renderStockDetail(detail) {
    const q = detail.quote;
    const s = detail.stock;
    const inWatch = state.watchlistCodes.includes(q.code);
    const up = q.change_pct > 0;
    $("#stockSummary").innerHTML = `<div class="stock-title">
      <h1>${esc(s.name)} <span class="muted">${esc(q.code)}</span></h1>
      <div class="sub">${esc(s.sector)} · ${esc(s.board)} · 数据 ${esc(detail.clock || "")}</div></div>
      <div class="quote-primary"><span class="price ${up ? "up" : "down"}">${num(q.price)}</span>
      <span class="pct ${up ? "up" : "down"}">${signed(q.change_pct)}%</span></div>`;
    $("#stockActions").innerHTML = `
      <button class="btn" data-watch-code="${esc(q.code)}" type="button">${icon("star")}${inWatch ? "移出自选" : "加自选"}</button>
      <button class="btn btn-primary" data-buy-code="${esc(q.code)}" type="button">${icon("plus")}模拟买入</button>`;

    const i = detail.indicators_tail || {};
    const rows = [
      ["MA5", num(lastValue(i.ma5))], ["MA10", num(lastValue(i.ma10))],
      ["MA20", num(lastValue(i.ma20))], ["MACD", num(lastValue(i.macd))],
      ["KDJ K", num(lastValue(i.kdj_k), 1)], ["RSI14", num(lastValue(i.rsi), 1)],
      ["ATR", num(lastValue(i.atr))], ["量比", num(q.volume_ratio)],
      ["换手", num(q.turnover) + "%"], ["成交额", fmtAmount(q.amount)],
      ["PE", num(q.pe)], ["PB", num(q.pb)],
      ["涨停价", num(q.limit_up)], ["跌停价", num(q.limit_down)],
    ];
    $("#stockSide").innerHTML = `<div class="side-block">
      <h3>行情指标</h3><div class="info-grid">${rows
        .map(([k, v]) => `<div class="item"><span class="k">${esc(k)}</span><strong>${v}</strong></div>`)
        .join("")}</div></div>
      <div class="side-block"><h3>当前信号</h3>
      ${(detail.signals || []).map((sig) => `<div class="side-signal">
        <div class="top"><strong>${esc(sig.strategy_name)}</strong><span>${strengthBadge(sig.strength)}${qualityBadge(sig.quality)}</span></div>
        <div class="reason">${(sig.reasons || []).join("；")}</div>
      </div>`).join("") || `<div class="empty-state">暂无当前信号</div>`}</div>`;

    const winRows = Object.entries(detail.win_rates || {}).map(
      ([sid, rate]) =>
        `<div class="item"><span class="k">${esc(sid.toUpperCase())}</span><strong>${rate === null || rate === undefined ? "预热中" : num(rate, 1) + "%"}</strong></div>`
    ).join("");
    $("#detailSignals").innerHTML = `<table class="data-table"><thead><tr>
      <th>策略</th><th>触发</th><th>信号强度</th><th>质量</th><th>评分</th><th>建议</th></tr></thead><tbody>
      ${(detail.signals || []).map((sig) => `<tr class="stock-row" data-open-stock="${esc(sig.code)}">
        <td>${esc(sig.strategy_name)}</td><td>${esc(sig.window)}</td>
        <td>${strengthBadge(sig.strength)}</td><td>${qualityBadge(sig.quality)}</td>
        <td class="num">${num(sig.score, 0)}</td><td>${esc(sig.action)}</td></tr>`).join("") || `<tr><td colspan="6" class="muted">当前无信号；历史信号需在接入行情源后生成</td></tr>`}
    </tbody></table>`;
    $("#stockSide").insertAdjacentHTML(
      "beforeend",
      winRows
        ? `<div class="side-block"><h3>策略历史胜率</h3><div class="info-grid">${winRows}</div></div>`
        : ""
    );
  }

  function applyChartData(data) {
    if (!data || !data.bars || !data.bars.length) {
      $("#chartSummary").textContent = "暂无K线数据";
      return;
    }
    const latest = data.bars[data.bars.length - 1];
    klineChart.setData(data);
    state.overlay = state.overlay || "ma";
    klineChart.setOverlay(state.overlay);
    const periodText = { day: "日K", "5m": "5分钟", "1m": "1分钟", "15m": "15分钟" }[data.period] || data.period;
    $("#chartSummary").textContent = `${periodText}${data.replay ? " · 离线分钟回放" : ""} · 最新 ${latest.date}`;
    $("#chartClock").textContent = data.clock || "";
  }

  function setPeriod(period) {
    if (period === state.period) return;
    state.period = period;
    $$("#periodTabs .segment").forEach((el) => el.classList.toggle("active", el.dataset.period === period));
    reloadStockKline();
  }

  function setOverlay(overlay) {
    state.overlay = overlay;
    $$("#overlayGroup .overlay").forEach((el) => el.classList.toggle("active", el.dataset.overlay === overlay));
    if (klineChart) klineChart.setOverlay(overlay);
  }

  // ---------- backtest ----------
  const equityChart = new window.LineChart($("#equityCanvas"));

  async function loadBacktestView() {
    try {
      if (!state.strategies) {
        const data = await api("/api/strategies");
        state.strategies = data.strategies;
      }
      const sel = $("#backtestStrategy");
      sel.innerHTML = state.strategies.map((s) => `<option value="${s.id}">${esc(s.name)}（胜率 ${s.win_rate === null || s.win_rate === undefined ? "--" : num(s.win_rate, 1) + "%"}）</option>`).join("");
      sel.value = state.activeStrategy;
      renderBacktestMetrics(null);
    } catch (err) {
      toast("回测中心加载失败", err.message);
    }
  }

  async function runBacktest() {
    const strategy = $("#backtestStrategy").value || "s1";
    const capital = Number($("#backtestCapital").value || 1000000);
    state.activeStrategy = strategy;
    $("#backtestLoading").classList.remove("hidden");
    renderBacktestMetrics(null);
    try {
      const report = await api("/api/backtest/run", {
        method: "POST",
        body: { strategy, capital },
      });
      state.backtest = report;
      renderBacktestReport(report);
    } catch (err) {
      toast("回测运行失败", err.message);
    } finally {
      $("#backtestLoading").classList.add("hidden");
    }
  }

  function metricCards(metrics) {
    if (!metrics || !metrics.trades) {
      return `<div class="empty-state">运行回测后展示指标</div>`;
    }
    const items = [
      ["交易笔数", metrics.trades, ""], ["胜率", metrics.win_rate + "%", "每策略独立"],
      ["累计收益", signed(metrics.total_return) + "%", pctClass(metrics.total_return)],
      ["年化收益", signed(metrics.annual_return) + "%", pctClass(metrics.annual_return)],
      ["最大回撤", "-" + metrics.max_drawdown + "%", ""], ["盈亏比", num(metrics.profit_factor), ""],
      ["平均盈利", signed(metrics.avg_win) + "%", "up"], ["平均亏损", signed(metrics.avg_loss) + "%", "down"],
      ["平均持仓", num(metrics.avg_holding, 1) + "日", ""], ["夏普", num(metrics.sharpe), ""],
    ];
    return items.map(([label, value, cls]) => `<div class="metric"><span class="label">${esc(label)}</span><span class="value ${cls}">${value}</span><span class="hint">&nbsp;</span></div>`).join("");
  }

  function renderBacktestMetrics(report) {
    const m = report ? report.metrics : null;
    $("#backtestMetrics").innerHTML = metricCards(m);
    if (!report) {
      $("#backtestTrades").innerHTML = `<div class="empty-state">运行后显示最近成交</div>`;
      equityChart.setData([]);
      return;
    }
    $("#btPeriod").textContent = `样本 ${report.trade_count || 0} 笔执行 / ${report.all_signal_count || 0} 笔信号`;
    $("#btTradeCount").textContent = `${(report.trades || []).length} 笔最近成交`;
    $("#backtestTrades").innerHTML = `<table class="data-table"><thead><tr>
      <th>股票</th><th>策略</th><th>买入日</th><th>卖出日</th><th>持仓</th><th>收益</th></tr></thead><tbody>
      ${(report.trades || []).map((t) => `<tr class="stock-row" data-open-stock="${esc(t.code)}">
        <td>${stockCell(t.name, t.code, "")}</td><td>${esc(t.strategy_id.toUpperCase())}</td>
        <td>${esc(t.entry_date)}</td><td>${esc(t.exit_date)}</td><td class="num">${num(t.holding_days, 0)}日</td>
        <td class="num ${pctClass(t.pnl_pct)}">${signed(t.pnl_pct)}%</td></tr>`).join("")}</tbody></table>`;
    equityChart.setData(report.equity_curve || []);
  }

  function renderBacktestReport(report) {
    state.backtest = report;
    renderBacktestMetrics(report);
  }

  // ---------- paper ----------
  async function loadPaperView() {
    try {
      const [paper, watch] = await Promise.all([api("/api/paper"), api("/api/watchlist")]);
      state.paper = paper;
      state.watchlistCodes = watch.codes;
      renderPaper(paper, watch.codes);
    } catch (err) {
      toast("自选与模拟盘加载失败", err.message);
    }
  }

  function renderPaper(paper, codes) {
    if (!paper) return;
    $("#paperCashTag").textContent = "可用资金 ¥" + num(paper.cash, 0);
    const rows = codes.map((code) => state.quotes.find((q) => q.code === code)).filter(Boolean);
    $("#watchTable").innerHTML = `<table class="data-table"><thead><tr>
      <th>股票</th><th>现价</th><th>涨跌</th><th>量比</th><th>操作</th></tr></thead><tbody>
      ${rows.map((r) => `<tr class="stock-row" data-open-stock="${esc(r.code)}">
        <td>${stockCell(r.name, r.code, r.sector)}</td>
        <td class="num">${num(r.price)}</td>
        <td class="num ${pctClass(r.change_pct)}">${signed(r.change_pct)}%</td>
        <td class="num">${num(r.volume_ratio)}</td>
        <td><button class="btn btn-sm" data-buy-code="${esc(r.code)}" data-stop="1" type="button">${icon("plus")}买入</button></td></tr>`).join("")}
    </tbody></table>`;
    const positions = Object.values(paper.positions || []);
    $("#positionTable").innerHTML = `<table class="data-table"><thead><tr>
      <th>股票</th><th>持股</th><th>成本</th><th>现价</th><th>浮动</th><th>操作</th></tr></thead><tbody>
      ${positions.map((p) => {
        const q = state.quotes.find((x) => x.code === p.code);
        const cur = q ? q.price : p.avg_price;
        const pnl = (cur / p.avg_price - 1) * 100;
        return `<tr class="stock-row" data-open-stock="${esc(p.code)}">
          <td>${stockCell(p.name, p.code, "")}</td><td class="num">${p.shares}</td>
          <td class="num">${num(p.avg_price)}</td><td class="num">${num(cur)}</td>
          <td class="num ${pctClass(pnl)}">${signed(pnl)}%</td>
          <td><button class="btn btn-sm" data-sell-code="${esc(p.code)}" data-stop="1" type="button">卖出</button></td></tr>`;
      }).join("") || `<tr><td colspan="6" class="muted">暂无模拟持仓</td></tr>`}
    </tbody></table>`;
    $("#orderTable").innerHTML = `<table class="data-table"><thead><tr>
      <th>时间</th><th>委托</th><th>股票</th><th>方向</th><th>价格</th><th>数量</th><th>策略</th></tr></thead><tbody>
      ${(paper.orders || []).map((o) => `<tr>
        <td>${esc(o.time)}</td><td>#${o.id}</td><td>${esc(o.name)} ${esc(o.code)}</td>
        <td class="${o.action === "buy" ? "up" : "down"}">${o.action === "buy" ? "买入" : "卖出"}</td>
        <td class="num">${num(o.price)}</td><td class="num">${o.shares}</td><td>${esc(o.strategy || "manual")}</td></tr>`).join("") || `<tr><td colspan="7" class="muted">暂无委托</td></tr>`}
    </tbody></table>`;
  }

  // ---------- global events ----------
  async function paperBuy(code) {
    try {
      const paper = await api("/api/paper/orders", {
        method: "POST",
        body: { code, action: "buy", amount: 100000, strategy: "manual" },
      });
      state.paper = paper;
      toast("模拟买入成交", `${code} 100 元档已加入持仓`);
      if (state.view === "paper") renderPaper(paper, state.watchlistCodes);
    } catch (err) {
      toast("模拟买入失败", err.message);
    }
  }

  async function paperSell(code) {
    try {
      const paper = await api("/api/paper/orders", {
        method: "POST",
        body: { code, action: "sell" },
      });
      state.paper = paper;
      toast("模拟卖出成交", code);
      if (state.view === "paper") renderPaper(paper, state.watchlistCodes);
    } catch (err) {
      toast("模拟卖出失败", err.message);
    }
  }

  async function toggleWatch(code) {
    try {
      const watch = await api("/api/watchlist", {
        method: state.watchlistCodes.includes(code) ? "DELETE" : "POST",
        body: { code },
      });
      state.watchlistCodes = watch.codes;
      toast("自选已更新", code);
      if (state.stockCode === code) {
        const detail = await api(`/api/stocks/${code}`);
        renderStockDetail(detail);
      }
    } catch (err) {
      toast("自选更新失败", err.message);
    }
  }

  async function search(query) {
    if (!query || query.trim().length < 1) {
      $("#searchResults").classList.add("hidden");
      return;
    }
    try {
      const data = await api("/api/search?q=" + encodeURIComponent(query.trim()));
      if (!data.length) {
        $("#searchResults").innerHTML = `<div class="empty-state">没有匹配的股票</div>`;
        $("#searchResults").classList.remove("hidden");
        return;
      }
      $("#searchResults").innerHTML = data
        .map(
          (r) => `<button class="search-item" data-open-stock="${esc(r.code)}" type="button">
            <span class="left"><strong>${esc(r.name)}</strong><span class="code">${esc(r.code)} · ${esc(r.sector)}</span></span>
            <span class="${pctClass(r.change_pct)}">${signed(r.change_pct)}%</span></button>`
        )
        .join("");
      $("#searchResults").classList.remove("hidden");
    } catch (err) {
      $("#searchResults").innerHTML = `<div class="empty-state">搜索失败</div>`;
      $("#searchResults").classList.remove("hidden");
    }
  }

  function connectStream() {
    if (!window.EventSource) return;
    const es = new EventSource("/api/stream");
    es.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (err) {
        return;
      }
      if (!data) return;
      state.quotes = data.quotes || [];
      state.signals = data.signals || state.signals;
      clockText(data.clock);
      const previousKeys = state.lastSignalKeys;
      if (data.signal_event) {
        (data.signals || []).forEach((s) => {
          const key = `${s.strategy_id}:${s.code}:${s.quality}:${s.score}`;
          if (!previousKeys.has(key) && s.quality === "高") {
            toast("新信号 高质量", `${s.strategy_name} · ${s.name} ${signed(s.change_pct)}%`);
          }
          previousKeys.add(key);
        });
      }
      if (state.view === "dashboard") {
        renderMarketTable(null);
      } else if (state.view === "paper") {
        loadPaperView();
      } else if (state.view === "strategies" && state.strategies) {
        renderStrategySignals();
      }
    };
    es.onerror = () => {};
  }

  function bindEvents() {
    renderNav();
    document.addEventListener("click", async (event) => {
      const nav = event.target.closest("[data-nav]");
      if (nav) {
        location.hash = nav.dataset.nav === "dashboard" ? "#/" : "#/" + nav.dataset.nav;
        return;
      }
      const strategy = event.target.closest("[data-strategy]");
      if (strategy) {
        state.activeStrategy = strategy.dataset.strategy;
        renderStrategySidebar();
        renderStrategyRules();
        renderStrategySignals();
        return;
      }
      const stock = event.target.closest("[data-open-stock]");
      if (stock && !event.target.closest("[data-stop]")) {
        openStock(stock.dataset.openStock);
        return;
      }
      const buy = event.target.closest("[data-buy-code]");
      if (buy) {
        event.stopPropagation();
        paperBuy(buy.dataset.buyCode);
        return;
      }
      const sell = event.target.closest("[data-sell-code]");
      if (sell) {
        event.stopPropagation();
        paperSell(sell.dataset.sellCode);
        return;
      }
      const watch = event.target.closest("[data-watch-code]");
      if (watch) {
        toggleWatch(watch.dataset.watchCode);
        return;
      }
      const goBt = event.target.closest("[data-goto-backtest]");
      if (goBt) {
        state.activeStrategy = goBt.dataset.gotoBacktest;
        location.hash = "#/backtest";
        return;
      }
      const period = event.target.closest("#periodTabs .segment");
      if (period) {
        setPeriod(period.dataset.period);
        return;
      }
      const overlay = event.target.closest("#overlayGroup .overlay");
      if (overlay) {
        setOverlay(overlay.dataset.overlay);
        return;
      }
      const tab = event.target.closest("#marketTabs .segment");
      if (tab) {
        state.marketTab = tab.dataset.market;
        $$("#marketTabs .segment").forEach((el) => el.classList.toggle("active", el === tab));
        renderMarketTable(null);
        return;
      }
      if (!event.target.closest(".search-wrap")) {
        $("#searchResults").classList.add("hidden");
      }
    });

    $("#refreshBtn").addEventListener("click", loadDashboard);
    $("#backBtn").addEventListener("click", () => (location.hash = "#/"));
    $("#qualityFilter").addEventListener("change", (event) => {
      state.quality = event.target.value;
      renderStrategySignals();
    });
    ["#strategyPriceMin", "#strategyPriceMax"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("input", () => {
        clearTimeout(state.screenerTimer);
        state.screenerTimer = setTimeout(() => renderStrategySignals(), 220);
      });
    });
    const resetStrategyPrice = $("#resetStrategyPriceBtn");
    if (resetStrategyPrice) {
      resetStrategyPrice.addEventListener("click", () => {
        ["#strategyPriceMin", "#strategyPriceMax"].forEach((id) => {
          if ($(id)) $(id).value = "";
        });
        renderStrategySignals();
      });
    }
    ["#filterPriceMin", "#filterPriceMax", "#filterPctMin", "#filterPctMax", "#filterVolMin", "#filterTurnMin"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("input", () => {
        clearTimeout(state.screenerTimer);
        state.screenerTimer = setTimeout(() => renderMarketTable(null), 260);
      });
    });
    ["filterSector", "filterBoard", "filterStrength", "filterQuality"].forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("change", () => renderMarketTable(null));
    });
    const resetBtn = $("#resetScreenerBtn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        ["#filterPriceMin", "#filterPriceMax", "#filterPctMin", "#filterPctMax", "#filterVolMin", "#filterTurnMin"].forEach((id) => {
          if ($(id)) $(id).value = "";
        });
        ["filterSector", "filterBoard", "filterStrength", "filterQuality"].forEach((id) => {
          if ($(id)) $(id).value = "all";
        });
        renderMarketTable(null);
      });
    }
    $("#runBacktestBtn").addEventListener("click", runBacktest);
    $("#backtestStrategy").addEventListener("change", () => {
      state.activeStrategy = $("#backtestStrategy").value;
    });
    $("#globalSearch").addEventListener("input", (event) => {
      clearTimeout(state.searchTimer);
      const value = event.target.value.trim();
      state.searchTimer = setTimeout(() => search(value), 260);
    });
    $("#globalSearch").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const first = $("#searchResults [data-open-stock]");
        if (first) openStock(first.dataset.openStock);
      }
    });
    window.addEventListener("hashchange", route);
  }

  function init() {
    bindEvents();
    connectStream();
    route();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
