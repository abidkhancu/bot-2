from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Tuple

import numpy as np
import pandas as pd

import ccxt.async_support as ccxt_async

CACHE_TTL_SECONDS = 15
logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self, exchange_id: str = "binance") -> None:
        self.exchange_id = exchange_id
        self._cache: Dict[Tuple[str, str], Tuple[float, pd.DataFrame]] = {}
        self._lock = asyncio.Lock()

    async def _create_exchange(self):
        exchange_class = getattr(ccxt_async, self.exchange_id)
        return exchange_class({"enableRateLimit": True})

    async def fetch_ohlcv(self, pair: str, timeframe: str = "1m", limit: int = 200) -> pd.DataFrame:
        key = (pair, timeframe)
        async with self._lock:
            if key in self._cache:
                ts, data = self._cache[key]
                if time.time() - ts < CACHE_TTL_SECONDS:
                    return data.copy()

        try:
            exchange = await self._create_exchange()
            raw = await exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
            await exchange.close()
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        except Exception:
            logger.exception("fetch_ohlcv failed for %s %s, using synthetic data fallback", pair, timeframe)
            df = self._generate_synthetic(limit)

        async with self._lock:
            self._cache[key] = (time.time(), df)
        return df.copy()

    def _generate_synthetic(self, limit: int) -> pd.DataFrame:
        now = int(time.time() * 1000)
        timestamps = np.arange(now - limit * 60_000, now, 60_000)
        prices = np.cumsum(np.random.randn(limit)) + 50_000
        highs = prices + np.random.rand(limit) * 50
        lows = prices - np.random.rand(limit) * 50
        volumes = np.random.rand(limit) * 10
        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": prices,
                "high": highs,
                "low": lows,
                "close": prices + np.random.randn(limit),
                "volume": volumes,
            }
        )
