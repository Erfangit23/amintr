"""
XAUUSD AutoTrader — Configuration
All settings centralized here. Managed via management bot or direct edits.
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"
CONFIG_EXAMPLE_PATH = Path(__file__).parent / "config.example.json"


@dataclass
class TraderConfig:
    tg_api_id: int = 0
    tg_api_hash: str = ""
    tg_phone: str = ""
    tg_channels: list = field(default_factory=lambda: [
        "@gold_alicxzos110",
        "@Xsd_Gold_SignaIs1",
    ])
    mt5_path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    mt5_server: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_symbol: str = "XAUUSD"
    lot_size: float = 0.01
    max_sl_pips: int = 150
    max_sl_pips_daily: int = 500
    tp_target: int = 2
    magic_number: int = 20260701
    slippage: int = 30
    deviation: int = 20
    mgmt_bot_token: str = ""
    mgmt_admin_ids: list = field(default_factory=list)
    mgmt_password: str = "Amin123"
    bot_active: bool = True
    daily_sl_hit: float = 0.0
    daily_sl_reset_date: str = ""


DEFAULT = TraderConfig()


def load() -> TraderConfig:
    if not CONFIG_PATH.exists():
        # First run — create from example or defaults
        cfg = DEFAULT
        if CONFIG_EXAMPLE_PATH.exists():
            try:
                raw = json.loads(CONFIG_EXAMPLE_PATH.read_text(encoding="utf-8"))
                merged = asdict(DEFAULT)
                merged.update(raw)
                cfg = TraderConfig(**merged)
            except Exception:
                pass
        save(cfg)
        log.info("Created config.json from defaults — edit it with your credentials")
        return cfg

    raw_text = CONFIG_PATH.read_text(encoding="utf-8")

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        # Show exactly where the error is
        lines = raw_text.split("\n")
        err_line = e.lineno
        log.critical(
            "config.json is broken at line %d, column %d: %s",
            e.lineno, e.colno, e.msg,
        )
        if err_line <= len(lines):
            log.critical("Problem line %d: %s", err_line, lines[err_line - 1].strip())
        log.critical("Fix your config.json or delete it to generate a fresh one.")
        raise SystemExit(
            f"\n\n!!! config.json syntax error at line {e.lineno} !!!\n"
            f"{e.msg}\n\n"
            f"→ Fix: delete config.json and copy config.example.json to config.json,\n"
            f"  then edit it with your real credentials.\n"
            f"→ Or manually fix the JSON error at line {e.lineno}.\n"
        ) from e

    merged = asdict(DEFAULT)
    merged.update(raw)
    return TraderConfig(**merged)


def save(cfg: TraderConfig):
    CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
