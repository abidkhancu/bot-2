# Crypto Trading Bot (Paper Trading MVP)

Full-stack paper trading bot focused on speed, modularity, and extensibility.

## Features
- FastAPI backend with async market data (CCXT), indicator engine (RSI/EMA/MACD), and strategy engine.
- In-memory storage with abstractions for signals, trades, settings, and market scans.
- Paper trading engine with balance tracking, TP/SL automation, and configurable risk.
- Auto-trading controls (start/stop bot, enable/disable auto trading, risk, TP/SL, max trades, enable database flag for future DB hooks).
- Market scanner and manual trading assistant suggestions.
- React + Tailwind dashboard with live signals, trades, settings, scanner, and controls.

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
npm run dev   # or npm run build for production
```

Set `VITE_API_BASE` to point the UI to your backend (defaults to `http://localhost:8000`).

## API Endpoints
- `GET /health`
- `GET /prices`
- `GET /signals`
- `POST /signals/generate`
- `GET /trades`
- `GET /portfolio`
- `POST /start-bot`
- `POST /stop-bot`
- `GET /settings`
- `POST /settings`
- `POST /auto-trade/{enabled}`
- `POST /scan-market`
- `GET /manual-suggestions`
