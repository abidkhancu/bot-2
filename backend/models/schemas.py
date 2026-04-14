from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Mode(str, Enum):
    paper = "paper"
    live = "live"


class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorSet(BaseModel):
    rsi: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    regression_mid: Optional[float] = None
    regression_upper: Optional[float] = None
    regression_lower: Optional[float] = None
    regression_strength: Optional[float] = None


class SignalSide(str, Enum):
    buy = "BUY"
    sell = "SELL"


class Signal(BaseModel):
    pair: str
    timeframe: str
    side: SignalSide
    entry: float
    stop_loss: float
    take_profit: float
    confidence: float
    indicators: IndicatorSet


class TradeStatus(str, Enum):
    open = "open"
    closed = "closed"


class Trade(BaseModel):
    id: str
    pair: str
    side: SignalSide
    entry: float
    stop_loss: float
    take_profit: float
    quantity: float
    status: TradeStatus
    pnl: float = 0.0
    exit_price: Optional[float] = None


class Settings(BaseModel):
    risk_per_trade: float = Field(0.01, ge=0.0, le=1.0)
    take_profit_pct: float = Field(0.02, ge=0.0)
    stop_loss_pct: float = Field(0.01, ge=0.0)
    max_open_trades: int = Field(3, ge=1)
    buy_rsi_threshold: float = Field(40, ge=0, le=100)
    sell_rsi_threshold: float = Field(55, ge=0, le=100)
    mode: Mode = Mode.paper
    enable_database: bool = False
    auto_trading_enabled: bool = False
    bot_running: bool = False
    auto_trade_timeframe: str = "1h"
    auto_trade_pair: str = "ALL"
    auto_trade_interval_seconds: int = Field(60, ge=15, le=3600)
    auto_trade_max_pairs: int = Field(30, ge=1, le=200)
    min_signal_confidence: float = Field(0.35, ge=0.0, le=1.0)
    min_market_score: float = Field(0.3, ge=0.0, le=1.0)
    use_smart_strategy: bool = True
    min_trend_strength: float = Field(0.0015, ge=0.0, le=0.5)
    min_regression_strength: float = Field(0.15, ge=0.0, le=1.0)


class MarketScanResult(BaseModel):
    pair: str
    price: float
    score: float
    trend: str
    volume: float
    rsi: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None


class ManualSuggestion(BaseModel):
    pair: str
    entry: float
    stop_loss: float
    take_profit: float
    reason: str
    confidence: float


class Health(BaseModel):
    status: str
    bot_running: bool
    auto_trading_enabled: bool


class PricesResponse(BaseModel):
    pair: str
    timeframe: str
    candles: List[Candle]
    indicators: IndicatorSet


class Portfolio(BaseModel):
    balance_usdt: float
    balance: float
    initial_balance_usdt: float
    open_trades: int
    closed_trades: int
    total_pnl: float
    roi_pct: float
    win_rate: float
