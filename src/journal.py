"""
Trade journal — logs every signal and trade outcome.
Also tracks daily SL so we can enforce budget.
"""
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from config import TraderConfig, load, save
from signal_parser import ParsedSignal

log = logging.getLogger(__name__)

JOURNAL_PATH = Path(__file__).parent / "trade_journal.jsonl"


def log_signal_processed(signal: ParsedSignal, ticket: Optional[int], reason: str = ""):
    entry = {
        "ts": datetime.now().isoformat(),
        "channel": signal.channel,
        "direction": signal.direction,
        "entry1": signal.entry1,
        "stoploss": signal.stoploss,
        "tp_used": signal.targets,
        "ticket": ticket,
        "reason": reason or ("placed" if ticket else "skipped"),
    }
    with JOURNAL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    status = "EXECUTED" if ticket else "SKIPPED"
    log.info("JOURNAL | %s | %s | %s | ticket=%s", status, signal.channel, reason, ticket)
    # Daily SL tracking is handled in mt5_trader.place_limit_order() — not here


def log_trade_closed(ticket: int, profit: float, reason: str = ""):
    entry = {
        "ts": datetime.now().isoformat(),
        "event": "closed",
        "ticket": ticket,
        "profit": profit,
        "reason": reason,
    }
    with JOURNAL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("JOURNAL | CLOSED | ticket=%d | profit=%.2f | %s", ticket, profit, reason)
