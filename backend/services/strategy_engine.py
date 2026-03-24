from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.models.schemas import IndicatorSet, Settings, Signal, SignalSide


class StrategyEngine:
    def __init__(self) -> None:
        self._confidence_floor = 0.3

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
            confidence = self._confidence_floor + (settings.buy_rsi_threshold - indicators.rsi) / 100
            return Signal(
                pair=pair,
                timeframe=timeframe,
                side=SignalSide.buy,
                entry=price,
                take_profit=price * (1 + tp_pct),
                stop_loss=price * (1 - sl_pct),
                confidence=min(round(confidence, 2), 1.0),
                indicators=indicators,
            )

        # SELL condition
        if indicators.rsi > settings.sell_rsi_threshold:
            confidence = self._confidence_floor + (indicators.rsi - settings.sell_rsi_threshold) / 100
            return Signal(
                pair=pair,
                timeframe=timeframe,
                side=SignalSide.sell,
                entry=price,
                take_profit=price * (1 - tp_pct),
                stop_loss=price * (1 + sl_pct),
                confidence=min(round(confidence, 2), 1.0),
                indicators=indicators,
            )

        return None
