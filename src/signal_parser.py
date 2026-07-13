"""
Signal parser — extracts trade signals from two known channel formats.
Returns a normalised dict or None if parsing fails.
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedSignal:
    channel: str           # friendly channel label
    direction: str         # BUY / SELL
    entry1: float          # entry  (first / NOW price)
    entry2: Optional[float] = None
    stoploss: float = 0.0
    targets: list = None   # list of TP prices
    raw_text: str = ""

    def __post_init__(self):
        if self.targets is None:
            self.targets = []


# ─────────────────────────── Format 1: @gold_alicxzos110 ───────────────────────────
RE_FMT1_HEADER = re.compile(
    r"📊\s*XAUUSD\s+(BUY|SELL)\s+NOW\s*\(\s*(\d+(?:\.\d+)?)\s*\)",
    re.IGNORECASE,
)
RE_FMT1_TARGET = re.compile(r"TARGET\s*(\d+)\s*\(\s*(\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)
RE_FMT1_SL = re.compile(r"STOP\s*LOSS\s*\(\s*(\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)


def _parse_fmt1(text: str) -> Optional[ParsedSignal]:
    header = RE_FMT1_HEADER.search(text)
    if not header:
        return None
    direction = header.group(1).upper()
    entry = float(header.group(2))

    targets: list[tuple[int, float]] = []
    for m in RE_FMT1_TARGET.finditer(text):
        targets.append((int(m.group(1)), float(m.group(2))))

    sl_match = RE_FMT1_SL.search(text)
    stoploss = float(sl_match.group(1)) if sl_match else 0.0

    if not targets or stoploss == 0.0:
        return None

    # sort by target number
    targets.sort(key=lambda x: x[0])
    tp_prices = [t[1] for t in targets]

    return ParsedSignal(
        channel="@gold_alicxzos110",
        direction=direction,
        entry1=entry,
        stoploss=stoploss,
        targets=tp_prices,
        raw_text=text,
    )


# ─────────────────────────── Format 2: @Xsd_Gold_SignaIs1 ───────────────────────────
RE_FMT2_HEADER = re.compile(
    r"XAUUSD\s+(BUY|SELL)\s+NOW\s+(\d+(?:\.\d+)?)\s*:+",
    re.IGNORECASE,
)
RE_FMT2_TARGET = re.compile(r"Tp\s*(\d+)\s*[🔽⬇️]\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
RE_FMT2_SL = re.compile(r"SL\s+(\d+(?:\.\d+)?)", re.IGNORECASE)


def _parse_fmt2(text: str) -> Optional[ParsedSignal]:
    header = RE_FMT2_HEADER.search(text)
    if not header:
        return None
    direction = header.group(1).upper()
    entry = float(header.group(2))

    targets: list[tuple[int, float]] = []
    for m in RE_FMT2_TARGET.finditer(text):
        targets.append((int(m.group(1)), float(m.group(2))))

    sl_match = RE_FMT2_SL.search(text)
    stoploss = float(sl_match.group(1)) if sl_match else 0.0

    if not targets or stoploss == 0.0:
        return None

    targets.sort(key=lambda x: x[0])
    tp_prices = [t[1] for t in targets]

    return ParsedSignal(
        channel="@Xsd_Gold_SignaIs1",
        direction=direction,
        entry1=entry,
        stoploss=stoploss,
        targets=tp_prices,
        raw_text=text,
    )


# ─────────────────────────── Dispatcher ───────────────────────────
PARSERS = [
    _parse_fmt1,
    _parse_fmt2,
]


def parse(text: str, channel_friendly: str = "") -> Optional[ParsedSignal]:
    """Try all format parsers; return first successful match."""
    for parser in PARSERS:
        result = parser(text)
        if result is not None:
            if channel_friendly:
                result.channel = channel_friendly
            return result
    return None
