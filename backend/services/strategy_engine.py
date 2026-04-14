from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.models.schemas import IndicatorSet, Settings, Signal, SignalSide


class StrategyEngine:
    # Tuned to reward clearer EMA separation while capping trend impact on confidence.
    TREND_STRENGTH_MULTIPLIER = 2.0
    TREND_CONFIDENCE_CAP = 0.2

    def __init__(self) -> None:
        self._confidence_floor = 0.3

    def _signal_confidence(self, base: float, indicators: IndicatorSet, is_buy: bool) -> float:
        confidence = base

        trend_strength = self._trend_strength_ratio(indicators)
        if trend_strength is not None:
            # The scaling with cap keeps trend impact meaningful but bounded:
            # it rewards clear trend separation while preventing trend from overpowering
            # RSI, MACD, and regression components in overall confidence.
            confidence += min(
                trend_strength * self.TREND_STRENGTH_MULTIPLIER,
                self.TREND_CONFIDENCE_CAP,
            )

        if indicators.macd_histogram is not None:
            if (is_buy and indicators.macd_histogram > 0) or (not is_buy and indicators.macd_histogram < 0):
                confidence += min(abs(indicators.macd_histogram), 0.1)

        if indicators.regression_strength is not None:
            confidence += min(indicators.regression_strength * 0.2, 0.2)

        return min(max(confidence, self._confidence_floor), 1.0)

    def _trend_strength_ratio(self, indicators: IndicatorSet) -> Optional[float]:
        if (
            indicators.ema_50 is None
            or indicators.ema_200 is None
            or indicators.ema_200 <= 1e-6
        ):
            return None
        return abs(indicators.ema_50 - indicators.ema_200) / indicators.ema_200

    def _passes_smart_filters(
        self,
        *,
        is_buy: bool,
        price: float,
        indicators: IndicatorSet,
        settings: Settings,
    ) -> bool:
        if not settings.use_smart_strategy:
            return True

        trend_strength = self._trend_strength_ratio(indicators)
        if trend_strength is None:
            return False
        if trend_strength < settings.min_trend_strength:
            return False

        if (indicators.regression_strength or 0.0) < settings.min_regression_strength:
            return False

        if indicators.macd_histogram is None:
            return False

        if is_buy:
            return (
                price > indicators.ema_50
                and indicators.ema_50 > indicators.ema_200
                and indicators.macd_histogram > 0
            )

        return (
            price < indicators.ema_50
            and indicators.ema_50 < indicators.ema_200
            and indicators.macd_histogram < 0
        )

    def generate_signal(
        self,
        pair: str,
        timeframe: str,
        df: pd.DataFrame,
        indicators: IndicatorSet,
        settings: Settings,
    ) -> Optional[Signal]:
        if df.empty or indicators.rsi is None or indicators.ema_200 is None:
            return None

        price = float(df["close"].iloc[-1])
        tp_pct = settings.take_profit_pct
        sl_pct = settings.stop_loss_pct

        # BUY condition
        if (
            price > indicators.ema_200
            and indicators.rsi < settings.buy_rsi_threshold
            and self._passes_smart_filters(
                is_buy=True,
                price=price,
                indicators=indicators,
                settings=settings,
            )
        ):
            confidence = self._signal_confidence(
                self._confidence_floor + (settings.buy_rsi_threshold - indicators.rsi) / 100,
                indicators,
                is_buy=True,
            )
            return Signal(
                pair=pair,
                timeframe=timeframe,
                side=SignalSide.buy,
                entry=price,
                take_profit=price * (1 + tp_pct),
                stop_loss=price * (1 - sl_pct),
                confidence=confidence,
                indicators=indicators,
            )

        # SELL condition
        if (
            indicators.rsi > settings.sell_rsi_threshold
            and self._passes_smart_filters(
                is_buy=False,
                price=price,
                indicators=indicators,
                settings=settings,
            )
        ):
            confidence = self._signal_confidence(
                self._confidence_floor + (indicators.rsi - settings.sell_rsi_threshold) / 100,
                indicators,
                is_buy=False,
            )
            return Signal(
                pair=pair,
                timeframe=timeframe,
                side=SignalSide.sell,
                entry=price,
                take_profit=price * (1 - tp_pct),
                stop_loss=price * (1 + sl_pct),
                confidence=confidence,
                indicators=indicators,
            )

        return None
