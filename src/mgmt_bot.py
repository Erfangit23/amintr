"""
Management Telegram bot — raw Telegram HTTP API (no python-telegram-bot).
Zero dependencies beyond httpx + asyncio. Polls getUpdates, replies via sendMessage.
"""
import asyncio
import json
import logging
from typing import Optional

import httpx

from config import TraderConfig, load, save
from mt5_trader import get_open_positions, get_open_orders, is_connected

log = logging.getLogger(__name__)

_BASE = "https://api.telegram.org"
_TOKEN: str = ""
_ADMIN_IDS: set[int] = set()
_AUTHED: set[int] = set()
_CLIENT: Optional[httpx.AsyncClient] = None


def _api(method: str, **params):
    """Call a Telegram API method."""
    url = f"{_BASE}/bot{_TOKEN}/{method}"
    return _CLIENT.post(url, json=params, timeout=15)


# ── Keyboard builder ──
def _inline_kb(rows: list[list[tuple[str, str]]]):
    return {
        "inline_keyboard": [[
            {"text": t, "callback_data": d} for t, d in row
        ] for row in rows]
    }


async def _send(chat_id: int, text: str, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if kb:
        payload["reply_markup"] = kb
    try:
        await _api("sendMessage", **payload)
    except Exception as e:
        log.warning("sendMessage failed: %s", e)


async def _edit(chat_id: int, msg_id: int, text: str, kb=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown"}
    if kb:
        payload["reply_markup"] = kb
    try:
        await _api("editMessageText", **payload)
    except Exception:
        pass  # message may be unchanged


# ── Menu ──
def _menu_kb(cfg: TraderConfig):
    return _inline_kb([
        [("Pause" if cfg.bot_active else "Resume", "toggle")],
        [("Report", "report")],
        [
            ("Lot 0.01", "lot:0.01"),
            ("Lot 0.02", "lot:0.02"),
            ("Lot 0.05", "lot:0.05"),
        ],
        [
            ("TP1", "tp:1"),
            ("TP2", "tp:2"),
            ("TP3", "tp:3"),
            ("TP4", "tp:4"),
        ],
        [
            ("Set Max SL/trade", "set:maxsl"),
            ("Set Max SL/day", "set:maxslday"),
        ],
    ])


async def _show_menu(chat_id: int, cfg: TraderConfig, edit_msg_id: int = 0):
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
    kb = _menu_kb(cfg)
    if edit_msg_id:
        await _edit(chat_id, edit_msg_id, text, kb)
    else:
        await _send(chat_id, text, kb)


# ── Callback handler ──
async def _handle_callback(cq: dict, awaiting: dict):
    chat_id = cq["message"]["chat"]["id"]
    msg_id = cq["message"]["message_id"]
    uid = cq["from"]["id"]
    data = cq.get("data", "")

    if uid not in _AUTHED:
        await _edit(chat_id, msg_id, "Session expired. Send password again.")
        return

    cfg = load()

    if data == "toggle":
        cfg.bot_active = not cfg.bot_active
        save(cfg)
        await _show_menu(chat_id, cfg, msg_id)

    elif data == "report":
        positions = get_open_positions(cfg.magic_number)
        orders = get_open_orders(cfg.magic_number)
        msg = f"*Current Report*\n\nOpen positions: {len(positions)}\nPending orders: {len(orders)}\n"
        if positions:
            for p in positions:
                ptype = "BUY" if p.type == 0 else "SELL"
                msg += f"  #{p.ticket} {ptype} Entry={p.price_open:.2f} SL={p.sl:.2f} TP={p.tp:.2f} P/L={p.profit:.2f}\n"
        if orders:
            for o in orders:
                otype = "BUY_LIMIT" if o.type == 2 else "SELL_LIMIT"
                msg += f"  #{o.ticket} {otype} Price={o.price_open:.2f} SL={o.sl:.2f} TP={o.tp:.2f}\n"
        if not positions and not orders:
            msg += "No open trades.\n"
        await _edit(chat_id, msg_id, msg, _inline_kb([
            [("Back", "back")]
        ]))

    elif data.startswith("lot:"):
        cfg.lot_size = float(data.split(":")[1])
        save(cfg)
        await _show_menu(chat_id, cfg, msg_id)

    elif data.startswith("tp:"):
        cfg.tp_target = int(data.split(":")[1])
        save(cfg)
        await _show_menu(chat_id, cfg, msg_id)

    elif data == "set:maxsl":
        awaiting[uid] = ("maxsl", chat_id, msg_id)
        await _edit(chat_id, msg_id, "Send new max SL per trade (pips), e.g. `120`:",
                     _inline_kb([[("Cancel", "back")]]))

    elif data == "set:maxslday":
        awaiting[uid] = ("maxslday", chat_id, msg_id)
        await _edit(chat_id, msg_id, "Send new max total SL per day (pips), e.g. `500`:",
                     _inline_kb([[("Cancel", "back")]]))

    elif data == "back":
        awaiting.pop(uid, None)
        await _show_menu(chat_id, cfg, msg_id)


# ── Polling loop ──
async def poll_loop(cfg: TraderConfig):
    global _TOKEN, _ADMIN_IDS, _CLIENT
    _TOKEN = cfg.mgmt_bot_token
    _ADMIN_IDS = set(cfg.mgmt_admin_ids)
    offset = 0
    awaiting: dict[int, tuple] = {}  # uid -> (what, chat_id, msg_id)

    _CLIENT = httpx.AsyncClient(timeout=httpx.Timeout(15.0))

    log.info("Management bot polling started (raw API mode)")

    while True:
        try:
            resp = await _api("getUpdates", offset=offset, timeout=20)
            data = resp.json()
        except Exception as e:
            log.warning("getUpdates error: %s — retrying in 3s", e)
            await asyncio.sleep(3)
            continue

        if not data.get("ok"):
            await asyncio.sleep(1)
            continue

        for upd in data["result"]:
            offset = upd["update_id"] + 1

            # ── Message ──
            msg = upd.get("message")
            if msg and "text" in msg:
                uid = msg["from"]["id"]
                chat_id = msg["chat"]["id"]
                text = msg["text"].strip()

                if uid not in _ADMIN_IDS:
                    continue

                # Auth
                if uid not in _AUTHED:
                    if text == cfg.mgmt_password:
                        _AUTHED.add(uid)
                        await _send(chat_id, "Authenticated. Welcome!")
                        await _show_menu(chat_id, cfg)
                    else:
                        await _send(chat_id, "Wrong password.")
                    continue

                # Check if awaiting input
                if uid in awaiting:
                    what, prev_chat, prev_msg = awaiting.pop(uid)
                    if what == "maxsl":
                        try:
                            val = int(text)
                            if 10 <= val <= 500:
                                cfg.max_sl_pips = val
                                save(cfg)
                                await _send(chat_id, f"Max SL/trade set to {val} pips.")
                            else:
                                await _send(chat_id, "Must be 10-500.")
                        except ValueError:
                            await _send(chat_id, "Invalid number.")
                    elif what == "maxslday":
                        try:
                            val = int(text)
                            if 50 <= val <= 5000:
                                cfg.max_sl_pips_daily = val
                                save(cfg)
                                await _send(chat_id, f"Max SL/day set to {val} pips.")
                            else:
                                await _send(chat_id, "Must be 50-5000.")
                        except ValueError:
                            await _send(chat_id, "Invalid number.")
                    await _show_menu(chat_id, cfg)

                elif text == "/start":
                    await _show_menu(chat_id, cfg)

            # ── Callback Query ──
            cq = upd.get("callback_query")
            if cq:
                await _api("answerCallbackQuery", callback_query_id=cq["id"])
                await _handle_callback(cq, awaiting)

        await asyncio.sleep(0.8)


async def start_bot(cfg: TraderConfig):
    """Start management bot polling."""
    global _POLL_TASK
    _POLL_TASK = asyncio.create_task(poll_loop(cfg))


async def stop_bot():
    global _CLIENT
    if _CLIENT:
        await _CLIENT.aclose()
        _CLIENT = None
    log.info("Management bot stopped")


def send_report(msg: str, cfg: TraderConfig):
    """Fire-and-forget report to all admin ids."""
    if not _CLIENT or not cfg.mgmt_admin_ids:
        return
    async def _send():
        for uid in cfg.mgmt_admin_ids:
            try:
                await _api("sendMessage", chat_id=uid, text=msg)
            except Exception:
                pass
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_send())
        else:
            loop.run_until_complete(_send())
    except Exception:
        pass
