"""
Position monitor — polls open positions and detects SL/TP hits.
Reports closures via journal and management bot.
"""
import asyncio
import logging
import MetaTrader5 as mt5

from config import TraderConfig, load, save
from mt5_trader import get_open_positions
from journal import log_trade_closed
from mgmt_bot import send_report

log = logging.getLogger(__name__)

# Track seen positions to detect closes
_seen_tickets: set[int] = set()


async def monitor_loop(cfg: TraderConfig, interval: float = 3.0):
    """Continuously poll open positions. Report when a position closes."""
    global _seen_tickets
    while True:
        try:
            if not cfg.bot_active:
                await asyncio.sleep(interval)
                continue

            positions = get_open_positions(cfg.magic_number)
            current_tickets = set()
            for p in positions:
                current_tickets.add(p.ticket)
                if p.ticket not in _seen_tickets:
                    _seen_tickets.add(p.ticket)
                    log.info("New position detected: #%d %s Entry=%.2f SL=%.2f TP=%.2f",
                             p.ticket, "BUY" if p.type == 0 else "SELL",
                             p.price_open, p.sl, p.tp)
                    send_report(
                        f"🆕 Position #{p.ticket}\n"
                        f"{'BUY' if p.type == 0 else 'SELL'} XAUUSD\n"
                        f"Entry: {p.price_open:.2f}  SL: {p.sl:.2f}  TP: {p.tp:.2f}",
                        cfg,
                    )

            # Detect closures
            closed = _seen_tickets - current_tickets
            for ticket in closed:
                _seen_tickets.discard(ticket)
                # Look up the closed position history to get P/L and reason
                history = mt5.history_deals_get(position=ticket)
                profit = 0.0
                reason = "closed"
                if history and len(history) > 0:
                    profit = sum(d.profit for d in history)
                    for deal in history:
                        if deal.entry == mt5.DEAL_ENTRY_OUT:
                            rv = deal.reason
                            if rv == mt5.DEAL_REASON_SL:
                                reason = "SL"
                            elif rv == mt5.DEAL_REASON_TP:
                                reason = "TP"
                            else:
                                reason = "Manual/Other"

                log_trade_closed(ticket, profit, reason)

                emoji = "OK" if profit > 0 else ("XX" if profit < 0 else "--")
                send_report(
                    f"{emoji} Trade #{ticket} closed\n"
                    f"P/L: {profit:+.2f}  Reason: {reason}",
                    cfg,
                )

        except Exception:
            log.exception("Monitor error")

        await asyncio.sleep(interval)
