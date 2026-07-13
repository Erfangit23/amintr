"""
Main entry point — ties everything together.
Run this 24/7 on the Windows VPS.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

from config import load, TraderConfig
from signal_parser import parse, ParsedSignal
from mt5_trader import connect, disconnect, place_limit_order, is_connected
from tg_listener import start_listener, stop_listener
from mgmt_bot import start_bot as start_mgmt, stop_bot as stop_mgmt, send_report
from monitor import monitor_loop
from journal import log_signal_processed

# ── Logging ──
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "autotrader.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("main")

# ── Dedup: ignore repeated signals within N seconds ──
_last_signal_hash: str = ""
_last_signal_time: float = 0.0
DEDUP_WINDOW = 60.0  # seconds


def _is_duplicate(signal: ParsedSignal) -> bool:
    global _last_signal_hash, _last_signal_time
    now = time.time()
    h = f"{signal.channel}|{signal.direction}|{signal.entry1}|{signal.stoploss}"
    if h == _last_signal_hash and (now - _last_signal_time) < DEDUP_WINDOW:
        return True
    _last_signal_hash = h
    _last_signal_time = now
    return False


async def on_signal(channel_name: str, text: str):
    """Called by tg_listener for every new message from monitored channels."""
    cfg = load()

    if not cfg.bot_active:
        return

    signal = parse(text, channel_name)
    if signal is None:
        return

    if "XAUUSD" not in text.upper():
        return

    if _is_duplicate(signal):
        log.info("Duplicate signal from %s — ignoring", channel_name)
        return

    log.info(
        "Signal: %s | %s Entry=%.2f SL=%.2f TPs=%s",
        channel_name, signal.direction, signal.entry1, signal.stoploss, signal.targets,
    )

    # Reconnect MT5 if needed
    if not is_connected():
        log.warning("MT5 disconnected — reconnecting…")
        try:
            disconnect()
            connect(cfg)
        except Exception:
            log.exception("MT5 reconnect failed")
            log_signal_processed(signal, None, "mt5_disconnected")
            return

    # Place order — use configured TP target (1-indexed)
    tp_idx = cfg.tp_target - 1
    ticket = place_limit_order(cfg, signal, tp_idx)

    if ticket:
        log_signal_processed(signal, ticket, "placed")
        tp_price = signal.targets[tp_idx] if tp_idx < len(signal.targets) else "?"
        send_report(
            f"Signal executed\n"
            f"Channel: {signal.channel}\n"
            f"{signal.direction} XAUUSD\n"
            f"Entry: {signal.entry1:.2f}\n"
            f"SL: {signal.stoploss:.2f}\n"
            f"TP{cfg.tp_target}: {tp_price}\n"
            f"Lot: {cfg.lot_size}\n"
            f"Ticket: #{ticket}",
            cfg,
        )
    else:
        log_signal_processed(signal, None, "rejected_or_failed")
        send_report(
            f"Signal skipped\n"
            f"Channel: {signal.channel}\n"
            f"{signal.direction} Entry={signal.entry1:.2f}\n"
            f"Check logs for reason.",
            cfg,
        )


async def _safe_start_mgmt(cfg: TraderConfig):
    """Start management bot with retry."""
    for attempt in range(3):
        try:
            await start_mgmt(cfg)
            return
        except Exception as e:
            log.warning("Mgmt bot start attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(5 * (attempt + 1))
    log.error("Mgmt bot failed to start after 3 attempts")


async def main():
    cfg = load()
    log.info("=" * 60)
    log.info("XAUUSD AutoTrader starting")
    log.info("=" * 60)

    # 1. Connect MT5
    try:
        connect(cfg)
    except Exception as e:
        log.critical("MT5 connection failed: %s", e)
    else:
        send_report("AutoTrader started — MT5 connected.", cfg)

    # 2. Start management bot
    if cfg.mgmt_bot_token:
        await _safe_start_mgmt(cfg)

    # 3. Position monitor
    monitor_task = asyncio.create_task(monitor_loop(cfg))

    # 4. Telegram signal listener (blocks until disconnect)
    listener_task = asyncio.create_task(start_listener(cfg, on_signal))

    done, pending = await asyncio.wait(
        [listener_task, monitor_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cleanup
    for task in pending:
        task.cancel()
    await stop_listener()
    await stop_mgmt()
    disconnect()
    send_report("AutoTrader stopped.", cfg)
    log.info("AutoTrader shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Keyboard interrupt")
        disconnect()
