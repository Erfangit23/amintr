"""
Telegram signal listener using Telethon (user client).
Joins channels and delivers new messages to the signal handler.
"""
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from config import TraderConfig, save

log = logging.getLogger(__name__)

# global reference so management bot can request status
_CLIENT: TelegramClient | None = None
_LISTENER_TASK: asyncio.Task | None = None


def get_client() -> TelegramClient | None:
    return _CLIENT


async def start_listener(cfg: TraderConfig, on_signal):
    """
    Connect Telethon user client, resolve channel entities, and listen for new messages.
    `on_signal` is an async callback(channel_name: str, text: str).
    """
    global _CLIENT

    session_file = "tg_user_session"
    client = TelegramClient(session_file, cfg.tg_api_id, cfg.tg_api_hash)
    _CLIENT = client

    try:
        await client.start(phone=cfg.tg_phone)
    except SessionPasswordNeededError:
        log.error("2FA password required — edit config or login manually first")
        raise

    me = await client.get_me()
    log.info("Telegram user logged in as @%s (id=%d)", me.username, me.id)

    # Resolve channels
    entities = {}
    for ch_name in cfg.tg_channels:
        try:
            entity = await client.get_entity(ch_name)
            entities[ch_name] = entity
            log.info("Resolved channel: %s", ch_name)
        except Exception as e:
            log.warning("Cannot resolve %s: %s", ch_name, e)

    if not entities:
        raise RuntimeError("No channels resolved — check channel usernames and account membership")

    # Register handler for resolved entities
    @client.on(events.NewMessage(chats=list(entities.values())))
    async def handler(event):
        try:
            chat = await event.get_chat()
            title = getattr(chat, "title", "") or getattr(chat, "username", "unknown")
            await on_signal(title, event.raw_text or "")
        except Exception as ex:
            log.exception("Signal handler error: %s", ex)

    log.info("Listening on %d channels…", len(entities))
    await client.run_until_disconnected()


async def stop_listener():
    global _CLIENT
    if _CLIENT:
        await _CLIENT.disconnect()
        _CLIENT = None
    log.info("Telegram listener stopped")
