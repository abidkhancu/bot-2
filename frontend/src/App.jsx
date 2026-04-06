import { useCallback, useEffect, useMemo, useState } from "react";
import "./index.css";

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (typeof window !== "undefined" ? `${window.location.origin}/api` : "/api");
const REFRESH_MS = Number(import.meta.env.VITE_REFRESH_MS ?? 20000);
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h"];
const formatRegressionFit = (value) => {
  if (value === undefined || value === null) return "-";
  return `${(value * 100).toFixed(1)}%`;
};

const StatCard = ({ title, value, accent }) => (
  <div className="rounded-xl border border-white/10 bg-white/5 p-4 shadow-lg shadow-black/30 backdrop-blur">
    <p className="text-sm text-slate-300">{title}</p>
    <p className={`text-2xl font-semibold ${accent ? "text-emerald-300" : "text-white"}`}>
      {value}
    </p>
  </div>
);

const Pill = ({ label }) => (
  <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white">
    {label}
  </span>
);

const Section = ({ title, action, children }) => (
  <div className="rounded-2xl border border-white/10 bg-white/5 p-5 shadow-xl shadow-black/20 backdrop-blur">
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {action}
    </div>
    {children}
  </div>
);

const useApi = () => {
  const request = useCallback(async (path, options = {}) => {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }, []);
  return { request };
};

function App() {
  const { request } = useApi();
  const [signals, setSignals] = useState([]);
  const [trades, setTrades] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [settings, setSettings] = useState(null);
  const [settingsForm, setSettingsForm] = useState(null);
  const [scanResults, setScanResults] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [priceInfo, setPriceInfo] = useState(null);
  const [pairs, setPairs] = useState([]);
  const [selectedPair, setSelectedPair] = useState("BTC/USDT");
  const [selectedTimeframe, setSelectedTimeframe] = useState("1m");
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const pairsResp = await request("/pairs");
      const fetchedPairs = Array.isArray(pairsResp) ? pairsResp : [];
      setPairs(fetchedPairs);
      const activePair = fetchedPairs.includes(selectedPair) ? selectedPair : fetchedPairs[0] || selectedPair;
      if (activePair !== selectedPair) {
        setSelectedPair(activePair);
      }

      const [
        settingsResp,
        signalsResp,
        tradesResp,
        portfolioResp,
        scanResp,
        suggestionsResp,
        priceResp,
      ] = await Promise.all([
        request("/settings"),
        request("/signals"),
        request("/trades"),
        request("/portfolio"),
        request("/scan-market", {
          method: "POST",
          body: JSON.stringify({ pairs: [activePair], timeframe: selectedTimeframe }),
        }),
        request("/manual-suggestions"),
        request(
          `/prices?pair=${encodeURIComponent(activePair)}&timeframe=${encodeURIComponent(selectedTimeframe)}`,
        ),
      ]);
      setSettings(settingsResp);
      setSettingsForm(settingsResp);
      setSignals(signalsResp);
      setTrades(tradesResp);
      setPortfolio(portfolioResp);
      setScanResults(scanResp);
      setSuggestions(suggestionsResp);
      setPriceInfo(priceResp);
      setStatus("connected");
    } catch (err) {
      console.error(err);
      setStatus("backend unavailable");
    } finally {
      setLoading(false);
    }
  }, [request, selectedPair, selectedTimeframe]);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, REFRESH_MS);
    return () => clearInterval(interval);
  }, [loadAll]);

  const startBot = async () => {
    await request("/start-bot", { method: "POST" });
    await loadAll();
  };
  const stopBot = async () => {
    await request("/stop-bot", { method: "POST" });
    await loadAll();
  };
  const toggleAuto = async (enabled) => {
    const previous = settingsForm ? { ...settingsForm } : null;
    setSettingsForm((prev) => (prev ? { ...prev, auto_trading_enabled: enabled } : prev));
    try {
      await request(`/auto-trade/${enabled}`, { method: "POST" });
      await loadAll();
    } catch (err) {
      console.error(err);
      if (previous) setSettingsForm(previous);
      setStatus("backend unavailable");
    }
  };
  const generateSignal = async () => {
    await request(
      `/signals/generate?pair=${encodeURIComponent(selectedPair)}&timeframe=${encodeURIComponent(selectedTimeframe)}`,
      { method: "POST" },
    );
    await loadAll();
  };
  const runScan = async () => {
    await request("/scan-market", {
      method: "POST",
      body: JSON.stringify({ pairs: [selectedPair], timeframe: selectedTimeframe }),
    });
    await loadAll();
  };
  const saveSettings = async () => {
    await request("/settings", { method: "POST", body: JSON.stringify(settingsForm) });
    await loadAll();
  };

  const totals = useMemo(() => {
    const pnl = trades.reduce((acc, t) => acc + (t.pnl || 0), 0);
    const open = trades.filter((t) => t.status === "open").length;
    return { pnl, open };
  }, [trades]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black text-white">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <header className="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-wide text-emerald-300">Paper Trading MVP</p>
            <h1 className="text-3xl font-bold text-white">Crypto Trading Bot</h1>
            <p className="text-sm text-slate-300">Async FastAPI backend • React + Tailwind UI</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={generateSignal}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-900 shadow-lg shadow-emerald-500/30 transition hover:bg-emerald-400"
            >
              Generate Signal
            </button>
            <button
              onClick={runScan}
              className="rounded-lg border border-white/20 px-4 py-2 text-sm font-semibold text-white transition hover:border-white/40"
            >
              Scan Market
            </button>
            <Pill label={status || "loading..."} />
          </div>
        </header>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard
            title="Balance (USDT)"
            value={`$${portfolio ? portfolio.balance_usdt.toFixed(2) : "0"}`}
            accent
          />
          <StatCard title="Open Trades" value={portfolio ? portfolio.open_trades : totals.open} />
          <StatCard
            title="Closed Trades"
            value={portfolio ? portfolio.closed_trades : trades.length - totals.open}
          />
          <StatCard
            title="PnL / ROI"
            value={`$${portfolio ? portfolio.total_pnl.toFixed(2) : totals.pnl.toFixed(2)}`}
            accent
          />
        </div>
        {portfolio && (
          <div className="mt-3 flex flex-wrap gap-2">
            <Pill label={`ROI ${portfolio.roi_pct?.toFixed(2) ?? "0.00"}%`} />
            <Pill label={`Win Rate ${((portfolio.win_rate ?? 0) * 100).toFixed(1)}%`} />
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Section
            title="Bot Controls"
            action={
              <div className="flex gap-2">
                <button
                  onClick={startBot}
                  className="rounded-lg bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-900 hover:bg-emerald-400"
                >
                  Start
                </button>
                <button
                  onClick={stopBot}
                  className="rounded-lg bg-rose-500 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-400"
                >
                  Stop
                </button>
              </div>
            }
          >
            {settingsForm ? (
              <div className="space-y-3 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex flex-col gap-1 text-slate-200">
                    Risk per trade
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={settingsForm.risk_per_trade}
                      onChange={(e) => setSettingsForm({ ...settingsForm, risk_per_trade: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-slate-200">
                    TP %
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={settingsForm.take_profit_pct}
                      onChange={(e) => setSettingsForm({ ...settingsForm, take_profit_pct: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-slate-200">
                    SL %
                    <input
                      type="number"
                      min="0"
                      step="0.001"
                      value={settingsForm.stop_loss_pct}
                      onChange={(e) => setSettingsForm({ ...settingsForm, stop_loss_pct: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-slate-200">
                    Buy RSI threshold
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={settingsForm.buy_rsi_threshold}
                      onChange={(e) => setSettingsForm({ ...settingsForm, buy_rsi_threshold: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-slate-200">
                    Sell RSI threshold
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={settingsForm.sell_rsi_threshold}
                      onChange={(e) => setSettingsForm({ ...settingsForm, sell_rsi_threshold: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-slate-200">
                    Max open trades
                    <input
                      type="number"
                      min="1"
                      value={settingsForm.max_open_trades}
                      onChange={(e) => setSettingsForm({ ...settingsForm, max_open_trades: Number(e.target.value) })}
                      className="rounded border border-white/10 bg-white/5 px-3 py-2 text-white"
                    />
                  </label>
                </div>

                <div className="flex flex-wrap gap-3">
                  <label className="flex items-center gap-2 text-slate-200">
                    <input
                      type="checkbox"
                      checked={settingsForm.auto_trading_enabled}
                      onChange={(e) => toggleAuto(e.target.checked)}
                      className="h-4 w-4 accent-emerald-400"
                    />
                    Auto trading
                  </label>
                  <label className="flex items-center gap-2 text-slate-200">
                    <input
                      type="checkbox"
                      checked={settingsForm.enable_database}
                      onChange={(e) => setSettingsForm({ ...settingsForm, enable_database: e.target.checked })}
                      className="h-4 w-4 accent-emerald-400"
                    />
                    Enable Database (prep)
                  </label>
                  <Pill label={`Mode: ${settingsForm.mode}`} />
                  <Pill label={settings?.bot_running ? "Running" : "Stopped"} />
                </div>

                <button
                  onClick={saveSettings}
                  className="w-full rounded-lg bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
                >
                  Save Settings
                </button>
              </div>
            ) : (
              <p className="text-slate-400">Loading settings...</p>
            )}
          </Section>

          <Section
            title="Live Signal & Price"
            action={
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={selectedPair}
                  onChange={(e) => setSelectedPair(e.target.value)}
                  className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-white"
                >
                  {pairs.length === 0 && <option value={selectedPair}>{selectedPair}</option>}
                  {pairs.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <select
                  value={selectedTimeframe}
                  onChange={(e) => setSelectedTimeframe(e.target.value)}
                  className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs text-white"
                >
                  {TIMEFRAMES.map((tf) => (
                    <option key={tf} value={tf}>
                      {tf}
                    </option>
                  ))}
                </select>
                <Pill label={`${priceInfo?.pair ?? selectedPair} • ${priceInfo?.timeframe ?? selectedTimeframe}`} />
              </div>
            }
          >
            {priceInfo ? (
              (() => {
                const lastCandle =
                  priceInfo.candles && priceInfo.candles.length > 0
                    ? priceInfo.candles[priceInfo.candles.length - 1]
                    : null;
                return (
                  <div className="space-y-2 text-sm text-slate-200">
                    <div className="flex flex-wrap gap-2">
                      <Pill label={`RSI ${priceInfo.indicators.rsi?.toFixed(2) ?? "-"}`} />
                      <Pill label={`EMA50 ${priceInfo.indicators.ema_50?.toFixed(2) ?? "-"}`} />
                      <Pill label={`EMA200 ${priceInfo.indicators.ema_200?.toFixed(2) ?? "-"}`} />
                      <Pill label={`MACD ${priceInfo.indicators.macd?.toFixed(2) ?? "-"}`} />
                      <Pill label={`WReg Mid ${priceInfo.indicators.regression_mid?.toFixed(2) ?? "-"}`} />
                      <Pill
                        label={`WReg Band ${priceInfo.indicators.regression_lower?.toFixed(2) ?? "-"} / ${priceInfo.indicators.regression_upper?.toFixed(2) ?? "-"}`}
                      />
                      <Pill
                        label={`Fit ${formatRegressionFit(priceInfo.indicators.regression_strength)}`}
                      />
                    </div>
                    <p className="text-4xl font-semibold text-white">
                      ${lastCandle?.close?.toFixed(2) ?? "--"}
                    </p>
                    <p className="text-xs text-slate-400">
                      Last candle {lastCandle ? new Date(lastCandle.timestamp).toLocaleTimeString() : "--"}
                    </p>
                  </div>
                );
              })()
            ) : (
              <p className="text-slate-400">Awaiting price data...</p>
            )}
          </Section>

          <Section title="Manual Trading Assistant">
            {suggestions.length === 0 ? (
              <p className="text-slate-400">No suggestions yet.</p>
            ) : (
              <div className="space-y-3">
                {suggestions.map((s) => (
                  <div key={s.pair} className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold">{s.pair}</p>
                      <Pill label={`${Math.round(s.confidence * 100)}%`} />
                    </div>
                    <p className="text-slate-300">{s.reason}</p>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-200">
                      <div>
                        <p className="text-slate-400">Entry</p>
                        <p>{s.entry.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-slate-400">SL</p>
                        <p>{s.stop_loss.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-slate-400">TP</p>
                        <p>{s.take_profit.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Section title="Recent Signals">
            {signals.length === 0 ? (
              <p className="text-slate-400">No signals yet.</p>
            ) : (
              <div className="space-y-3">
                {signals.slice().reverse().map((sig, idx) => (
                  <div key={`${sig.pair}-${idx}`} className="rounded-lg border border-white/10 bg-white/5 p-3">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <Pill label={sig.side} />
                        <p className="font-semibold">{sig.pair}</p>
                      </div>
                      <p className="text-xs text-slate-400">{sig.timeframe}</p>
                    </div>
                    <div className="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-200">
                      <div>
                        <p className="text-slate-400">Entry</p>
                        <p>{sig.entry.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-slate-400">SL</p>
                        <p>{sig.stop_loss.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-slate-400">TP</p>
                        <p>{sig.take_profit.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-slate-400">Confidence</p>
                        <p>{Math.round(sig.confidence * 100)}%</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Trades">
            {trades.length === 0 ? (
              <p className="text-slate-400">No trades yet.</p>
            ) : (
              <div className="space-y-3">
                {trades
                  .slice()
                  .reverse()
                  .map((trade) => (
                    <div
                      key={trade.id}
                      className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Pill label={trade.side} />
                          <p className="font-semibold">{trade.pair}</p>
                        </div>
                        <Pill
                          label={`${trade.status} • $${trade.pnl.toFixed(2)}`}
                        />
                      </div>
                      <div className="mt-2 grid grid-cols-4 gap-2 text-xs text-slate-200">
                        <div>
                          <p className="text-slate-400">Entry</p>
                          <p>{trade.entry.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-slate-400">SL</p>
                          <p>{trade.stop_loss.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-slate-400">TP</p>
                          <p>{trade.take_profit.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-slate-400">Qty</p>
                          <p>{trade.quantity.toFixed(4)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </Section>
        </div>

        <div className="mt-6">
          <Section title="Market Scanner">
            {scanResults.length === 0 ? (
              <p className="text-slate-400">No scan data yet.</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {scanResults.slice(0, 6).map((row) => (
                  <div key={row.pair} className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold">{row.pair}</p>
                      <Pill label={`Score ${row.score}`} />
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-300">
                      <Pill label={`Price $${row.price?.toFixed(2) ?? "-"}`} />
                      <Pill label={row.trend} />
                      <Pill label={`RSI ${row.rsi?.toFixed(2) ?? "-"}`} />
                      <Pill label={`EMA50 ${row.ema_50?.toFixed(2) ?? "-"}`} />
                      <Pill label={`EMA200 ${row.ema_200?.toFixed(2) ?? "-"}`} />
                      <Pill label={`Vol ${row.volume.toFixed(2)}`} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>

        {loading && <p className="mt-4 text-sm text-slate-400">Refreshing data...</p>}
      </div>
    </div>
  );
}

export default App;
