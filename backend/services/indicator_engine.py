from __future__ import annotations

import numpy as np
import pandas as pd

from backend.models.schemas import IndicatorSet


class IndicatorEngine:
    def _ema(self, series: pd.Series, span: int):
        if series.empty:
            return None
        return float(series.ewm(span=span, adjust=False).mean().iloc[-1])

    def _rsi(self, series: pd.Series, period: int = 14):
        if len(series) < period + 1:
            return None
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0.0).rolling(window=period).mean()
        rs = gain / loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else None

    def _macd(self, series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        if series.empty:
            return None, None, None
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(hist.iloc[-1])

    def _weighted_regression_bands(
        self,
        series: pd.Series,
        period: int = 100,
        smooth: int = 5,
        std_mult: float = 2.0,
    ):
        if len(series) < period:
            return None, None, None, None

        recent = series.tail(period).astype(float).values
        x = np.arange(period, dtype=float)
        # 1.0 -> 2.0 gives a conservative recency bias (~2x weight to newest candles) for responsiveness without overfitting noise.
        weights = np.linspace(1.0, 2.0, period)
        slope, intercept = np.polyfit(x, recent, 1, w=weights)
        fit_line = slope * x + intercept
        smoothed = pd.Series(fit_line).rolling(window=smooth, min_periods=1).mean().values
        residual_std = float(np.std(recent - smoothed))
        mid = float(smoothed[-1])
        upper = float(mid + std_mult * residual_std)
        lower = float(mid - std_mult * residual_std)
        strength = float(np.clip(1 - (residual_std / max(abs(mid), 1e-6)), 0, 1))
        return mid, upper, lower, strength

    def compute(self, df: pd.DataFrame) -> IndicatorSet:
        if df.empty:
            return IndicatorSet()

        closes = df["close"]
        macd_line, signal_line, hist = self._macd(closes)
        reg_mid, reg_upper, reg_lower, reg_strength = self._weighted_regression_bands(closes)

        return IndicatorSet(
            rsi=self._rsi(closes),
            ema_50=self._ema(closes, span=50),
            ema_200=self._ema(closes, span=200),
            macd=macd_line,
            macd_signal=signal_line,
            macd_histogram=hist,
            regression_mid=reg_mid,
            regression_upper=reg_upper,
            regression_lower=reg_lower,
            regression_strength=reg_strength,
        )
