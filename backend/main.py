from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import (
    Health,
    ManualSuggestion,
    MarketScanResult,
    Portfolio,
    PricesResponse,
    Settings,
    Signal,
    SignalSide,
    Trade,
    TradeStatus,
)
from backend.services.indicator_engine import IndicatorEngine
from backend.services.market_data import MarketDataService
from backend.services.market_scanner import MarketScanner
from backend.services.paper_trading import PaperTradingEngine
from backend.services.storage import StorageService
from backend.services.strategy_engine import StrategyEngine

storage = StorageService()
market_data_service = MarketDataService()
indicator_engine = IndicatorEngine()
strategy_engine = StrategyEngine()
paper_trading_engine = PaperTradingEngine(storage)
market_scanner = MarketScanner(market_data_service, indicator_engine, storage)

DEFAULT_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "DOT/USDT",
    "LTC/USDT",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(market_scanner.scan(DEFAULT_PAIRS))
    yield


app = FastAPI(title="Crypto Trading Bot (Paper Trading)", lifespan=lifespan)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _as_candles(df) -> List[dict]:
    return [
        {
            "timestamp": int(row["timestamp"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in df.iterrows()
    ]


async def _generate_signal_for_pair(pair: str, timeframe: str, settings: Settings) -> Optional[Signal]:
    df = await market_data_service.fetch_ohlcv(pair, timeframe=timeframe, limit=250)
    indicators = indicator_engine.compute(df)
    signal = strategy_engine.generate_signal(pair, timeframe, df, indicators, settings)
    if signal:
        await storage.add_signal(signal)
        await paper_trading_engine.apply_signal(signal, settings)
        await paper_trading_engine.evaluate_tp_sl(signal.entry)
    return signal


@app.get("/health", response_model=Health)
async def health() -> Health:
    settings = storage.settings
    return Health(status="ok", bot_running=settings.bot_running, auto_trading_enabled=settings.auto_trading_enabled)


@app.get("/prices", response_model=PricesResponse)
async def get_prices(pair: str = "BTC/USDT", timeframe: str = "1m") -> PricesResponse:
    df = await market_data_service.fetch_ohlcv(pair, timeframe=timeframe, limit=200)
    indicators = indicator_engine.compute(df)
    await paper_trading_engine.evaluate_tp_sl(float(df["close"].iloc[-1]) if not df.empty else 0)
    return PricesResponse(pair=pair, timeframe=timeframe, candles=_as_candles(df), indicators=indicators)


@app.get("/signals", response_model=List[Signal])
async def list_signals() -> List[Signal]:
    return await storage.list_signals()


@app.post("/signals/generate", response_model=Optional[Signal])
async def generate_signal(pair: str = "BTC/USDT", timeframe: str = "1m") -> Optional[Signal]:
    return await _generate_signal_for_pair(pair, timeframe, storage.settings)


@app.get("/trades", response_model=List[Trade])
async def list_trades() -> List[Trade]:
    return await storage.list_trades()


@app.get("/portfolio", response_model=Portfolio)
async def portfolio() -> Portfolio:
    trades = await storage.list_trades()
    total_pnl = sum(t.pnl for t in trades)
    open_trades = len([t for t in trades if t.status == TradeStatus.open])
    closed_trades = len(trades) - open_trades
    return Portfolio(
        balance=storage.get_balance(),
        open_trades=open_trades,
        closed_trades=closed_trades,
        total_pnl=total_pnl,
    )


@app.post("/start-bot", response_model=Settings)
async def start_bot() -> Settings:
    new_settings = storage.settings.copy(deep=True, update={"bot_running": True})
    await storage.update_settings(new_settings)
    return new_settings


@app.post("/stop-bot", response_model=Settings)
async def stop_bot() -> Settings:
    new_settings = storage.settings.copy(deep=True, update={"bot_running": False})
    await storage.update_settings(new_settings)
    return new_settings


@app.get("/settings", response_model=Settings)
async def get_settings() -> Settings:
    return storage.settings


@app.post("/settings", response_model=Settings)
async def update_settings(settings: Settings) -> Settings:
    await storage.update_settings(settings)
    return storage.settings


@app.get("/pairs", response_model=List[str])
async def list_pairs() -> List[str]:
    return DEFAULT_PAIRS


@app.post("/scan-market", response_model=List[MarketScanResult])
async def scan_market(
    pairs: Optional[List[str]] = Body(None), timeframe: str = Body("1h")
) -> List[MarketScanResult]:
    pair_list = pairs or DEFAULT_PAIRS
    return await market_scanner.scan(pair_list, timeframe=timeframe)


@app.get("/manual-suggestions", response_model=List[ManualSuggestion])
async def manual_suggestions() -> List[ManualSuggestion]:
    return await storage.get_suggestions()


@app.post("/auto-trade/{enabled}", response_model=Settings)
async def toggle_auto_trading(enabled: bool) -> Settings:
    new_settings = storage.settings.copy(deep=True, update={"auto_trading_enabled": enabled})
    await storage.update_settings(new_settings)
    return new_settings
