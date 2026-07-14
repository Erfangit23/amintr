"""
Management Telegram bot (python-telegram-bot).
Allows admin to change settings, view reports, pause/resume.
Password: Amin123
"""
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TraderConfig, load, save
from mt5_trader import get_open_positions, get_open_orders, is_connected

log = logging.getLogger(__name__)

_APP: Optional[Application] = None
_authenticated: set[int] = set()


# ── helpers ──
async def _edit_or_reply(ctx, text: str, markup=None):
    """Update callback query message if possible, else send new."""
    if hasattr(ctx, "edit_message_text"):
        await ctx.edit_message_text(text, reply_markup=markup)
    else:
        await ctx.message.reply_text(text, reply_markup=markup)


async def _show_menu(ctx, cfg: TraderConfig):
    status = "ACTIVE" if cfg.bot_active else "PAUSED"
    mt5_ok = is_connected()
    mt5_status = "OK" if mt5_ok else "DOWN"

    text = (
        f"*XAUUSD AutoTrader Panel*\n\n"
        f"Status: {status}\n"
        f"MT5: {mt5_status}\n"
        f"Lot: {cfg.lot_size}\n"
        f"TP target: TP{cfg.tp_target}\n"
        f"Max SL/trade: {cfg.max_sl_pips} pips\n"
        f"Max SL/day: {cfg.max_sl_pips_daily} pips\n"
        f"Daily SL used: {cfg.daily_sl_hit:.1f} pips\n"
    )

    kb = [
        [InlineKeyboardButton(
            "Pause" if cfg.bot_active else "Resume", callback_data="toggle"
        )],
        [InlineKeyboardButton("Report", callback_data="report")],
        [
            InlineKeyboardButton("Lot 0.01", callback_data="lot:0.01"),
            InlineKeyboardButton("Lot 0.02", callback_data="lot:0.02"),
            InlineKeyboardButton("Lot 0.05", callback_data="lot:0.05"),
        ],
        [
            InlineKeyboardButton("TP1", callback_data="tp:1"),
            InlineKeyboardButton("TP2", callback_data="tp:2"),
            InlineKeyboardButton("TP3", callback_data="tp:3"),
            InlineKeyboardButton("TP4", callback_data="tp:4"),
        ],
        [
            InlineKeyboardButton("Set Max SL/trade", callback_data="set:maxsl"),
            InlineKeyboardButton("Set Max SL/day", callback_data="set:maxslday"),
        ],
    ]
    await _edit_or_reply(ctx, text, InlineKeyboardMarkup(kb))


# ── Handlers ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cfg = load()
    if uid not in cfg.mgmt_admin_ids:
        await update.message.reply_text("Not authorised.")
        return
    if uid in _authenticated:
        await _show_menu(update, cfg)
    else:
        await update.message.reply_text("Send password to continue.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unified text handler: password auth OR setting input."""
    uid = update.effective_user.id
    cfg = load()
    if uid not in cfg.mgmt_admin_ids:
        return

    text = (update.message.text or "").strip()

    # Auth path
    if uid not in _authenticated:
        if text == cfg.mgmt_password:
            _authenticated.add(uid)
            await update.message.reply_text("Authenticated. Welcome!")
            await _show_menu(update, cfg)
        else:
            await update.message.reply_text("Wrong password.")
        return

    # Setting-input path (user was asked for a value)
    awaiting = context.user_data.get("awaiting_input")
    if awaiting:
        context.user_data.pop("awaiting_input", None)
        if awaiting == "maxsl":
            try:
                val = int(text)
                if 10 <= val <= 500:
                    cfg.max_sl_pips = val
                    save(cfg)
                    await update.message.reply_text(f"Max SL/trade set to {val} pips.")
                else:
                    await update.message.reply_text("Must be 10-500.")
            except ValueError:
                await update.message.reply_text("Invalid number.")
        elif awaiting == "maxslday":
            try:
                val = int(text)
                if 50 <= val <= 5000:
                    cfg.max_sl_pips_daily = val
                    save(cfg)
                    await update.message.reply_text(f"Max SL/day set to {val} pips.")
                else:
                    await update.message.reply_text("Must be 50-5000.")
            except ValueError:
                await update.message.reply_text("Invalid number.")
        await _show_menu(update, cfg)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    cfg = load()

    if uid not in _authenticated:
        await query.edit_message_text("Session expired. Send password again.")
        return

    data = query.data

    if data == "toggle":
        cfg.bot_active = not cfg.bot_active
        save(cfg)
        await _show_menu(query, cfg)

    elif data == "report":
        positions = get_open_positions(cfg.magic_number)
        orders = get_open_orders(cfg.magic_number)
        msg = (
            f"*Current Report*\n\n"
            f"Open positions: {len(positions)}\n"
            f"Pending orders: {len(orders)}\n"
        )
        if positions:
            for p in positions:
                ptype = "BUY" if p.type == 0 else "SELL"
                msg += (
                    f"  #{p.ticket} {ptype} Entry={p.price_open:.2f} "
                    f"SL={p.sl:.2f} TP={p.tp:.2f} P/L={p.profit:.2f}\n"
                )
        if orders:
            for o in orders:
                otype = "BUY_LIMIT" if o.type == 2 else "SELL_LIMIT"
                msg += f"  #{o.ticket} {otype} Price={o.price_open:.2f} SL={o.sl:.2f} TP={o.tp:.2f}\n"
        if not positions and not orders:
            msg += "No open trades.\n"
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back", callback_data="back")]
            ]),
        )

    elif data.startswith("lot:"):
        cfg.lot_size = float(data.split(":")[1])
        save(cfg)
        await _show_menu(query, cfg)

    elif data.startswith("tp:"):
        cfg.tp_target = int(data.split(":")[1])
        save(cfg)
        await _show_menu(query, cfg)

    elif data == "set:maxsl":
        context.user_data["awaiting_input"] = "maxsl"
        await query.edit_message_text(
            "Send new max SL per trade (pips), e.g. `120`:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cancel", callback_data="back")]
            ]),
        )

    elif data == "set:maxslday":
        context.user_data["awaiting_input"] = "maxslday"
        await query.edit_message_text(
            "Send new max total SL per day (pips), e.g. `500`:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cancel", callback_data="back")]
            ]),
        )

    elif data == "back":
        await _show_menu(query, cfg)


async def start_bot(cfg: TraderConfig):
    """Start the management Telegram bot."""
    global _APP
    app = (
        Application.builder()
        .token(cfg.mgmt_bot_token)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(10)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    _APP = app
    log.info("Management bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=3.0,
        timeout=30,
    )
    log.info("Management bot polling started")


async def stop_bot():
    global _APP
    if _APP:
        await _APP.updater.stop()
        await _APP.stop()
        await _APP.shutdown()
        _APP = None
    log.info("Management bot stopped")


def send_report(msg: str, cfg: TraderConfig):
    """Fire-and-forget report to all admin ids via the running bot."""
    import asyncio as _asyncio

    if _APP is None or not cfg.mgmt_admin_ids:
        return

    async def _send():
        for uid in cfg.mgmt_admin_ids:
            try:
                await _APP.bot.send_message(chat_id=uid, text=msg)
            except Exception:
                pass

    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_send())
        else:
            loop.run_until_complete(_send())
    except Exception:
        pass
