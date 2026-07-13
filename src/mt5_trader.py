"""
MT5 connector & order execution.
Handles connection lifecycle, order placement, position monitoring.
"""
import logging
from datetime import datetime, date
from typing import Optional
import MetaTrader5 as mt5

from config import TraderConfig, load, save
from signal_parser import ParsedSignal

log = logging.getLogger(__name__)


class MT5Error(Exception):
    pass


def connect(cfg: TraderConfig) -> bool:
    """Initialise MT5 terminal and log in. Returns True on success."""
    if mt5.initialize(
        path=cfg.mt5_path,
        login=cfg.mt5_login,
        password=cfg.mt5_password,
        server=cfg.mt5_server,
    ):
        log.info("MT5 initialised — account %s on %s", cfg.mt5_login, cfg.mt5_server)
        info = mt5.account_info()
        if info is None:
            raise MT5Error("MT5 login failed — check credentials/server")
        log.info(
            "Balance=%.2f  Equity=%.2f  Leverage=%d",
            info.balance, info.equity, info.leverage,
        )
        # enable symbol
        if not mt5.symbol_select(cfg.mt5_symbol, True):
            raise MT5Error(f"Symbol {cfg.mt5_symbol} not available")
        return True
    else:
        raise MT5Error(f"MT5 initialize() failed: {mt5.last_error()}")


def disconnect():
    mt5.shutdown()
    log.info("MT5 disconnected")


def _pips_to_price(symbol: str, pips: float) -> float:
    """Convert pips to raw price distance for a symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return pips * 0.01  # XAUUSD fallback
    return pips * info.point * 10  # 1 pip = 10 points for XAUUSD


def _price_from_pips(symbol: str, pips: float) -> float:
    """Absolute price distance in symbol-native units."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return pips * 0.01
    return pips * info.point * 10


def calc_sl_pips(cfg: TraderConfig, signal: ParsedSignal) -> float:
    """Return |entry - sl| in pips.  For XAUUSD 1 pip = 0.10 in raw price."""
    pip_size = 0.10  # XAUUSD standard: 1 pip = $0.10
    return abs(signal.entry1 - signal.stoploss) / pip_size


def place_limit_order(
    cfg: TraderConfig,
    signal: ParsedSignal,
    tp_index: int,  # 0-based index into signal.targets
) -> Optional[int]:
    """
    Place a pending limit order for the parsed signal.
    tp_index selects which TP level (0 = TP1, 1 = TP2, ...)
    Returns ticket number or None.
    """
    symbol = cfg.mt5_symbol
    direction = signal.direction.upper()

    # ── absolute prices ──
    entry_price = signal.entry1  # the "NOW" price
    sl_price = signal.stoploss

    if tp_index >= len(signal.targets):
        log.error("TP index %d out of range (have %d targets)", tp_index, len(signal.targets))
        return None
    tp_price = signal.targets[tp_index]

    # ── safety check: SL pips ──
    sl_pips = calc_sl_pips(cfg, signal)
    if sl_pips > cfg.max_sl_pips:
        log.warning("SL %.1f pips > max allowed %d — skipping", sl_pips, cfg.max_sl_pips)
        return None

    # ── daily SL exposure budget (tracks cumulative SL of placed orders) ──
    today_str = date.today().isoformat()
    if cfg.daily_sl_reset_date != today_str:
        cfg.daily_sl_hit = 0.0
        cfg.daily_sl_reset_date = today_str
    if cfg.daily_sl_hit + sl_pips > cfg.max_sl_pips_daily:
        log.warning(
            "Daily SL exposure budget exceeded (%.1f + %.1f > %d pips) — skipping",
            cfg.daily_sl_hit, sl_pips, cfg.max_sl_pips_daily,
        )
        return None
    # Reserve the SL budget now
    cfg.daily_sl_hit += sl_pips
    save(cfg)

    # ── order type ──
    if direction == "BUY":
        order_type = mt5.ORDER_TYPE_BUY_LIMIT
    else:
        order_type = mt5.ORDER_TYPE_SELL_LIMIT

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": cfg.lot_size,
        "type": order_type,
        "price": entry_price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": cfg.deviation,
        "magic": cfg.magic_number,
        "comment": f"autoclaw_{signal.channel.lstrip('@')}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        err = mt5.last_error()
        log.error("Order failed: retcode=%s  error=%s", getattr(result, "retcode", "None"), err)
        return None

    log.info(
        "✅ LIMIT %s | Entry=%.2f  SL=%.2f  TP%d=%.2f  Lot=%.2f  Ticket=%d",
        direction, entry_price, sl_price, tp_index + 1, tp_price, cfg.lot_size, result.order,
    )
    return result.order


def get_open_positions(magic: int) -> list:
    """Return all open positions matching our magic number."""
    positions = mt5.positions_get()
    if positions is None:
        return []
    return [p for p in positions if p.magic == magic]


def get_open_orders(magic: int) -> list:
    orders = mt5.orders_get()
    if orders is None:
        return []
    return [o for o in orders if o.magic == magic]


def is_connected() -> bool:
    return mt5.terminal_info() is not None
