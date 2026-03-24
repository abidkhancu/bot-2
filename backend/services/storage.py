from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque, Dict, List

from backend.models.schemas import (
    ManualSuggestion,
    MarketScanResult,
    Settings,
    Signal,
    Trade,
)


class StorageService:
    def __init__(self, max_signals: int = 100) -> None:
        self._signals: Deque[Signal] = deque(maxlen=max_signals)
        self._trades: List[Trade] = []
        self._settings: Settings = Settings()
        self._suggestions: List[ManualSuggestion] = []
        self._scan_cache: List[MarketScanResult] = []
        self._balances: Dict[str, float] = {"USD": 1000.0}
        self._lock = asyncio.Lock()

    @property
    def settings(self) -> Settings:
        return self._settings

    def get_balance(self) -> float:
        return self._balances["USD"]

    async def update_settings(self, new_settings: Settings) -> Settings:
        async with self._lock:
            # Preserve start balance when toggling
            self._settings = new_settings
            return self._settings

    async def add_signal(self, signal: Signal) -> None:
        async with self._lock:
            self._signals.append(signal)

    async def list_signals(self) -> List[Signal]:
        async with self._lock:
            return list(self._signals)

    async def add_trade(self, trade: Trade) -> None:
        async with self._lock:
            self._trades.append(trade)

    async def list_trades(self) -> List[Trade]:
        async with self._lock:
            return list(self._trades)

    async def upsert_trade(self, trade: Trade) -> None:
        async with self._lock:
            for idx, t in enumerate(self._trades):
                if t.id == trade.id:
                    self._trades[idx] = trade
                    break
            else:
                self._trades.append(trade)

    async def update_balance(self, delta: float) -> float:
        async with self._lock:
            self._balances["USD"] += delta
            return self._balances["USD"]

    async def set_scan_results(self, results: List[MarketScanResult]) -> None:
        async with self._lock:
            self._scan_cache = results

    async def get_scan_results(self) -> List[MarketScanResult]:
        async with self._lock:
            return list(self._scan_cache)

    async def set_suggestions(self, suggestions: List[ManualSuggestion]) -> None:
        async with self._lock:
            self._suggestions = suggestions

    async def get_suggestions(self) -> List[ManualSuggestion]:
        async with self._lock:
            return list(self._suggestions)
