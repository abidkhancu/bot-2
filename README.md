# Crypto Trading Bot (Paper Trading MVP)

Full-stack paper trading bot focused on speed, modularity, and extensibility.

## Features
- FastAPI backend with async market data (CCXT), indicator engine (RSI/EMA/MACD + weighted regression bands), and strategy engine.
- In-memory storage with abstractions for signals, trades, settings, and market scans.
- Paper trading engine with dummy USDT balance tracking, TP/SL automation, and configurable risk.
- Auto-trading controls (start/stop bot, enable/disable auto trading, risk, TP/SL, max trades, enable database flag for future DB hooks).
- Market scanner with enhanced multi-factor scoring and manual trading assistant suggestions.
- React + Tailwind dashboard with live signals, trades, settings, scanner, auto-trading toggle, and pair/timeframe selector.

## Getting Started

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# Default dev proxy targets http://localhost:8000 via /api.
# Or set a custom backend:
# echo 'VITE_API_BASE=http://localhost:8000' > .env
npm run dev   # or npm run build for production
```

Set `VITE_API_BASE` to point the UI to your backend (defaults to `http://localhost:8000`).

### Using the dashboard
- Use the pair and timeframe selectors (top of the Live Signal card) to focus the UI on a specific market.
- Generate Signal and Scan Market actions use the currently selected pair/timeframe.
- Enable “Auto trading” from Bot Controls to allow the strategy to place paper trades automatically.
- Portfolio cards show dummy USDT balance, ROI, and win rate to evaluate bot performance.

## API Endpoints
- `GET /health`
- `GET /pairs`
- `GET /prices?pair=BTC/USDT&timeframe=1m`
- `GET /signals`
- `POST /signals/generate?pair=BTC/USDT&timeframe=1m`
- `GET /trades`
- `GET /portfolio`
- `POST /start-bot`
- `POST /stop-bot`
- `GET /settings`
- `POST /settings`
- `POST /auto-trade/{enabled}`
- `POST /scan-market`
- `GET /manual-suggestions`
