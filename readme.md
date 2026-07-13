# XAUUSD AutoTrader

24/7 Python bot that reads Telegram trading signals and auto-executes limit orders on MetaTrader 5 for XAUUSD.

## How It Works

- Monitors **Telegram channels** in real-time via Telethon
- Parses signals from two supported channel formats
- Applies safety checks (max SL per trade, daily SL budget)
- Places **limit orders** on MT5 with exact entry, stop-loss, and take-profit
- **Management bot** lets you control settings via Telegram (pause, change lot, TP level, SL limits)
- Reports every trade execution and closure

## Quick Start (On VPS)

1. Run `setup.bat` — creates venv + installs dependencies
2. Copy `src/config.example.json` to `src/config.json` and fill in your credentials
3. Make sure **MT5 is open and logged in**
4. Run `run_watchdog.bat` — auto-restarts on crash, runs 24/7

See **SETUP_GUIDE.txt** for complete step-by-step VPS setup instructions.

## Management Bot

Telegram bot with password `Amin123`. Controls:
- Pause / Resume trading
- Lot size (0.01 / 0.02 / 0.05)
- TP target (TP1 – TP4)
- Max SL per trade
- Max total SL per day
- Live position/order report

## Requirements

- Windows with Python 3.11+
- MetaTrader 5 installed and running
- Telegram account (joined to signal channels)
- Telegram API credentials (my.telegram.org)

## Structure

```
src/
├── main.py           ← Entry point
├── config.py         ← Typed config loader
├── signal_parser.py  ← Channel signal parsers
├── mt5_trader.py     ← MT5 connection & orders
├── tg_listener.py    ← Telegram signal listener
├── mgmt_bot.py       ← Management Telegram bot
├── monitor.py        ← Position/closure monitor
└── journal.py        ← Trade journal (JSONL)
```
