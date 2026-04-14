from __future__ import annotations

from typing import List

import numpy as np

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

    def _enhanced_score(self, indicators: IndicatorSet, price: float) -> float:
        score = 0.0
        total_weight = 0.0

        # RSI mean-reversion quality
        if indicators.rsi is not None:
            rsi_score = (50 - abs(50 - indicators.rsi)) / 50
            score += rsi_score * 0.3
            total_weight += 0.3

        # EMA trend quality
        if indicators.ema_50 is not None and indicators.ema_200 is not None and indicators.ema_200 != 0:
            trend_ratio = indicators.ema_50 / indicators.ema_200
            trend_score = float(np.clip((trend_ratio - 0.95) / 0.1, 0, 1))
            score += trend_score * 0.25
            total_weight += 0.25

        # Regression-band position + fit strength
        if (
            indicators.regression_lower is not None
            and indicators.regression_upper is not None
            and indicators.regression_upper > indicators.regression_lower
        ):
            band_pos = (price - indicators.regression_lower) / (
                indicators.regression_upper - indicators.regression_lower
            )
            band_score = float(np.clip(1 - abs(0.5 - band_pos) * 2, 0, 1))
            strength = indicators.regression_strength or 0.0
            score += ((band_score * 0.6) + (strength * 0.4)) * 0.25
            total_weight += 0.25

        # MACD momentum
        if indicators.macd_histogram is not None:
            momentum_score = float(np.clip((indicators.macd_histogram + 1) / 2, 0, 1))
            score += momentum_score * 0.2
            total_weight += 0.2

        if total_weight == 0:
            return 0.0
        return score / total_weight

    async def scan(self, pairs: List[str], timeframe: str = "1h") -> List[MarketScanResult]:
        results: List[MarketScanResult] = []
        for pair in pairs:
            df = await self.market_data.fetch_ohlcv(pair, timeframe=timeframe, limit=150)
            indicators: IndicatorSet = self.indicator_engine.compute(df)
            if df.empty:
                continue

            price = float(df["close"].iloc[-1])
            trend = "bullish" if indicators.ema_50 and indicators.ema_200 and indicators.ema_50 > indicators.ema_200 else "sideways"
            score = self._enhanced_score(indicators, price)

            result = MarketScanResult(
                pair=pair,
                price=price,
                score=score,
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
