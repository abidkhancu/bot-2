from __future__ import annotations

import uuid
from typing import List

from backend.models.schemas import Settings, Signal, SignalSide, Trade, TradeStatus
from backend.services.storage import StorageService


class PaperTradingEngine:
    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    async def _open_trades(self) -> List[Trade]:
        trades = await self.storage.list_trades()
        return [t for t in trades if t.status == TradeStatus.open]

    async def _has_open_trade(self, pair: str, side: SignalSide) -> bool:
        open_trades = await self._open_trades()
        return any(t.pair == pair and t.side == side for t in open_trades)

    async def apply_signal(self, signal: Signal, settings: Settings) -> None:
        if not settings.auto_trading_enabled or not settings.bot_running:
            return

        if signal.side == SignalSide.buy:
            await self._close_trades(signal.pair, side=SignalSide.sell, price=signal.entry)
            open_trades = await self._open_trades()
            if len(open_trades) >= settings.max_open_trades:
                return
            if await self._has_open_trade(signal.pair, SignalSide.buy):
                return
            await self._open_long(signal, settings)
            return

        await self._close_trades(signal.pair, side=SignalSide.buy, price=signal.entry)
        open_trades = await self._open_trades()
        if len(open_trades) >= settings.max_open_trades:
            return
        if await self._has_open_trade(signal.pair, SignalSide.sell):
            return
        await self._open_short(signal, settings)

    async def _open_long(self, signal: Signal, settings: Settings) -> None:
        balance = self.storage.get_balance()
        if signal.entry <= 0 or balance <= 0:
            return
        risk_amount = balance * settings.risk_per_trade
        risk_per_unit = max(signal.entry - signal.stop_loss, 1e-6)
        risk_based_quantity = max(risk_amount / risk_per_unit, 0.0)
        # Cap size by available-balance affordability after the positive-entry guard above.
        balance_limited_quantity = balance / signal.entry
        quantity = min(risk_based_quantity, balance_limited_quantity)
        if quantity <= 0:
            return
        trade = Trade(
            id=str(uuid.uuid4()),
            pair=signal.pair,
            side=signal.side,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            quantity=quantity,
            status=TradeStatus.open,
            pnl=0.0,
        )
        await self.storage.add_trade(trade)
        await self.storage.update_balance(-quantity * signal.entry)

    async def _open_short(self, signal: Signal, settings: Settings) -> None:
        balance = self.storage.get_balance()
        if signal.entry <= 0 or balance <= 0:
            return
        risk_amount = balance * settings.risk_per_trade
        risk_per_unit = max(signal.stop_loss - signal.entry, 1e-6)
        risk_based_quantity = max(risk_amount / risk_per_unit, 0.0)
        margin_limited_quantity = balance / signal.entry
        quantity = min(risk_based_quantity, margin_limited_quantity)
        if quantity <= 0:
            return
        trade = Trade(
            id=str(uuid.uuid4()),
            pair=signal.pair,
            side=signal.side,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            quantity=quantity,
            status=TradeStatus.open,
            pnl=0.0,
        )
        await self.storage.add_trade(trade)
        await self.storage.update_balance(-quantity * signal.entry)

    async def _close_trades(self, pair: str, side: SignalSide, price: float) -> None:
        trades = await self.storage.list_trades()
        for trade in trades:
            if trade.status == TradeStatus.closed or trade.pair != pair or trade.side != side:
                continue
            await self._close_trade(trade, price)

    async def evaluate_tp_sl(self, latest_price: float, pair: str | None = None) -> None:
        trades = await self.storage.list_trades()
        for trade in trades:
            if trade.status == TradeStatus.closed:
                continue
            if pair is not None and trade.pair != pair:
                continue
            if trade.side == SignalSide.buy:
                if latest_price >= trade.take_profit or latest_price <= trade.stop_loss:
                    await self._close_trade(trade, latest_price)
            elif latest_price <= trade.take_profit or latest_price >= trade.stop_loss:
                await self._close_trade(trade, latest_price)

    async def _close_trade(self, trade: Trade, exit_price: float) -> None:
        if trade.side == SignalSide.buy:
            pnl = (exit_price - trade.entry) * trade.quantity
            settlement = trade.quantity * exit_price
        else:
            pnl = (trade.entry - exit_price) * trade.quantity
            settlement = (trade.quantity * trade.entry) + pnl
        trade.status = TradeStatus.closed
        trade.exit_price = exit_price
        trade.pnl = pnl
        await self.storage.upsert_trade(trade)
        await self.storage.update_balance(settlement)
