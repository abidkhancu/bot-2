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

    async def apply_signal(self, signal: Signal, settings: Settings) -> None:
        if not settings.auto_trading_enabled or not settings.bot_running:
            return

        if signal.side == SignalSide.buy:
            open_trades = await self._open_trades()
            if len(open_trades) >= settings.max_open_trades:
                return
            await self._open_long(signal, settings)
        else:
            await self._close_trades(signal)

    async def _open_long(self, signal: Signal, settings: Settings) -> None:
        balance = self.storage.get_balance()
        risk_amount = balance * settings.risk_per_trade
        risk_per_unit = max(signal.entry - signal.stop_loss, 1e-6)
        quantity = max(risk_amount / risk_per_unit, 0)
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

    async def _close_trades(self, signal: Signal) -> None:
        trades = await self.storage.list_trades()
        for trade in trades:
            if trade.status == TradeStatus.closed or trade.pair != signal.pair:
                continue
            await self._close_trade(trade, signal.entry)

    async def evaluate_tp_sl(self, latest_price: float) -> None:
        trades = await self.storage.list_trades()
        for trade in trades:
            if trade.status == TradeStatus.closed:
                continue
            if trade.side == SignalSide.buy:
                if latest_price >= trade.take_profit or latest_price <= trade.stop_loss:
                    await self._close_trade(trade, latest_price)

    async def _close_trade(self, trade: Trade, exit_price: float) -> None:
        pnl = (exit_price - trade.entry) * trade.quantity
        trade.status = TradeStatus.closed
        trade.exit_price = exit_price
        trade.pnl = pnl
        await self.storage.upsert_trade(trade)
        await self.storage.update_balance(trade.quantity * exit_price)
