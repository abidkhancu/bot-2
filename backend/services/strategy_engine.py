from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.models.schemas import IndicatorSet, Settings, Signal, SignalSide


class StrategyEngine:
    def __init__(self) -> None:
        self._confidence_floor = 0.3

    def _signal_confidence(self, base: float, indicators: IndicatorSet, is_buy: bool) -> float:
        confidence = base

        if indicators.ema_50 is not None and indicators.ema_200 is not None and indicators.ema_200 > 1e-6:
            trend_strength = abs(indicators.ema_50 - indicators.ema_200) / indicators.ema_200
            # The 2.0 scaling with 0.2 cap keeps trend impact meaningful but bounded:
            # it rewards clear trend separation while preventing trend from overpowering
            # RSI, MACD, and regression components in overall confidence.
            confidence += min(trend_strength * 2.0, 0.2)

        if indicators.macd_histogram is not None:
            if (is_buy and indicators.macd_histogram > 0) or (not is_buy and indicators.macd_histogram < 0):
                confidence += min(abs(indicators.macd_histogram), 0.1)

        if indicators.regression_strength is not None:
            confidence += min(indicators.regression_strength * 0.2, 0.2)

        return min(max(confidence, self._confidence_floor), 1.0)

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
        if price > indicators.ema_200 and indicators.rsi < settings.buy_rsi_threshold:
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
        if indicators.rsi > settings.sell_rsi_threshold:
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
