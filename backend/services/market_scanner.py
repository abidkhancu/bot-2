from __future__ import annotations

from typing import List

from backend.models.schemas import IndicatorSet, ManualSuggestion, MarketScanResult
from backend.services.indicator_engine import IndicatorEngine
from backend.services.market_data import MarketDataService
from backend.services.storage import StorageService


class MarketScanner:
    def __init__(
        self,
        market_data: MarketDataService,
        indicator_engine: IndicatorEngine,
        storage: StorageService,
    ) -> None:
        self.market_data = market_data
        self.indicator_engine = indicator_engine
        self.storage = storage

    async def scan(self, pairs: List[str], timeframe: str = "1h") -> List[MarketScanResult]:
        results: List[MarketScanResult] = []
        for pair in pairs:
            df = await self.market_data.fetch_ohlcv(pair, timeframe=timeframe, limit=150)
            indicators: IndicatorSet = self.indicator_engine.compute(df)
            if df.empty:
                continue

            price = float(df["close"].iloc[-1])
            trend = "bullish" if indicators.ema_50 and indicators.ema_200 and indicators.ema_50 > indicators.ema_200 else "sideways"
            score = 0.0
            if indicators.rsi:
                score += (50 - abs(50 - indicators.rsi)) / 50
            if indicators.ema_50 and indicators.ema_200:
                score += (indicators.ema_50 / indicators.ema_200)

            result = MarketScanResult(
                pair=pair,
                price=price,
                score=round(score, 2),
                trend=trend,
                volume=float(df["volume"].iloc[-1]),
                rsi=indicators.rsi,
                ema_50=indicators.ema_50,
                ema_200=indicators.ema_200,
            )
            results.append(result)

        results = sorted(results, key=lambda r: r.score, reverse=True)[:50]
        await self.storage.set_scan_results(results)
        await self.storage.set_suggestions(self._manual_suggestions(results))
        return results

    def _manual_suggestions(self, results: List[MarketScanResult]) -> List[ManualSuggestion]:
        suggestions: List[ManualSuggestion] = []
        for result in results[:3]:
            entry = result.price
            suggestions.append(
                ManualSuggestion(
                    pair=result.pair,
                    entry=entry,
                    stop_loss=entry * 0.99 if entry else 0,
                    take_profit=entry * 1.02 if entry else 0,
                    reason=f"Trend {result.trend} | score {result.score}",
                    confidence=min(result.score / 2, 1.0),
                )
            )
        return suggestions
