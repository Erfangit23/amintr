"""
XAUUSD AutoTrader — Configuration
All settings centralized here. Managed via management bot or direct edits.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


@dataclass
class TraderConfig:
    # ── Telegram (user client for signal listening) ──
    tg_api_id: int = 0
    tg_api_hash: str = ""
    tg_phone: str = ""  # for first login only; session file persists after

    # ── Telegram channels to monitor ──
    tg_channels: list = field(default_factory=lambda: [
        "@gold_alicxzos110",
        "@Xsd_Gold_SignaIs1",
    ])

    # ── MetaTrader 5 ──
    mt5_path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    mt5_server: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_symbol: str = "XAUUSD"

    # ── Trade settings ──
    lot_size: float = 0.01
    max_sl_pips: int = 150          # per trade; skip signal if SL > this
    max_sl_pips_daily: int = 500    # total daily SL hit before bot pauses
    tp_target: int = 2              # which TP level to use (1–7); default TP2
    magic_number: int = 20260701
    slippage: int = 30
    deviation: int = 20

    # ── Management bot ──
    mgmt_bot_token: str = ""        # BotFather token
    mgmt_admin_ids: list = field(default_factory=list)  # tg user ids
    mgmt_password: str = "Amin123"

    # ── Runtime ──
    bot_active: bool = True
    daily_sl_hit: float = 0.0
    daily_sl_reset_date: str = ""


DEFAULT = TraderConfig()


def load() -> TraderConfig:
    if CONFIG_PATH.exists():
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # merge into defaults (handles added fields after upgrade)
        merged = asdict(DEFAULT)
        merged.update(raw)
        cfg = TraderConfig(**merged)
    else:
        cfg = DEFAULT
        save(cfg)
    return cfg


def save(cfg: TraderConfig):
    CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
