# ⚡ Binance Futures Testnet Trading Bot

> A production-quality CLI trading bot for **Binance USDT-M Futures Testnet**.  
> Supports MARKET, LIMIT, STOP_MARKET, and STOP_LIMIT orders with a vibrant Retro-Futuristic terminal UI.

---

## 📁 Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST API wrapper (HMAC signing, retry logic)
│   ├── orders.py            # High-level order management & OrderResult DTO
│   ├── validators.py        # Strict input validation for all order parameters
│   └── logging_config.py   # Structured logging (rotating file + console)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── cli.py                   # Typer + Rich CLI entry point
├── .env.example             # Environment variable template
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Prerequisites
- Python 3.10 or higher
- pip

### 2. Clone / Navigate to the project
```bash
cd trading_bot
```

### 3. Create & activate a virtual environment
```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure API credentials

Copy `.env.example` to `.env` and fill in your Binance Testnet credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here
```

**Get testnet credentials at:** https://testnet.binancefuture.com  
Register → Log in → API Management → Create API Key

---

## 🚀 Usage

### Show help

```bash
python cli.py --help
python cli.py place-order --help
```

---

### 📊 Check current price

```bash
python cli.py price --symbol BTCUSDT
```

**Output:**
```
╭──────────── BTCUSDT  Current Price ─────────────╮
│                                                  │
│                   $63,412.00                     │
│                                                  │
╰──────────────────────────────────────────────────╯
```

---

### 🛒 Place a MARKET order (via flags)

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --qty 0.001
```

---

### 📋 Place a LIMIT order (via flags)

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type LIMIT \
  --qty 0.001 \
  --price 60000 \
  --tif GTC
```

---

### 🛑 Place a STOP_MARKET order (bonus)

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --qty 0.001 \
  --stop-price 58000
```

---

### 🔒 Place a STOP_LIMIT order (bonus)

```bash
python cli.py place-order \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_LIMIT \
  --qty 0.001 \
  --price 57800 \
  --stop-price 58000 \
  --tif GTC
```

---

### 🌀 Interactive mode (no flags needed)

```bash
python cli.py place-order --interactive
```

The CLI will prompt for each field with defaults:
```
  Symbol    [BTCUSDT]:
  Side      (BUY, SELL) [BUY]:
  Order type (MARKET, LIMIT, STOP_MARKET, STOP_LIMIT) [MARKET]:
  Quantity  [0.001]:
  Confirm order submission? [Y/n]:
```

---

### 📂 List open orders

```bash
# All symbols
python cli.py open-orders

# Filtered by symbol
python cli.py open-orders --symbol BTCUSDT
```

---

### ❌ Cancel an order

```bash
python cli.py cancel-order --symbol BTCUSDT --order-id 123456789
```

---

### 💼 Account overview

```bash
python cli.py account
```

---

## 🎨 CLI Theme

The terminal interface uses a **Dopamine / Retro-Futuristic** colour palette:

| Element | Colour |
|---------|--------|
| Headers & labels | Neon Cyan |
| Success messages | Neon Green |
| Error messages | Neon Red |
| Warnings | Neon Yellow |
| Borders | Neon Magenta |
| Field names | Medium Purple |
| BUY orders | Bright Green |
| SELL orders | Bright Red |

All colours comply with **WCAG AA contrast** requirements on dark terminal backgrounds.

---

## 📝 Logging

Logs are written to `logs/trading_bot.log` with automatic rotation (5 MB × 5 backups).

**Log format:**
```
[YYYY-MM-DD HH:MM:SS] [LEVEL   ] [module] Message
```

**Log levels:**
- `DEBUG` — Full API payloads (file only)
- `INFO` — Order lifecycle events
- `WARNING` — Recoverable issues, ignored parameters
- `ERROR` — API and validation failures
- `CRITICAL` — Unhandled exceptions

---

## 🧠 Architecture

```
CLI (cli.py)
  └── OrderManager (orders.py)
        ├── OrderValidator (validators.py)   ← validates inputs FIRST
        └── BinanceFuturesClient (client.py) ← signs & sends the request
              └── Binance Futures Testnet REST API
```

**Design principles:**
- **Separation of concerns** — each module has a single responsibility
- **Fail fast** — validation occurs before any network call
- **Decimal precision** — all prices/quantities use `decimal.Decimal` to avoid float errors
- **Retry logic** — network errors auto-retry up to 3 times with backoff
- **Context manager** — `BinanceFuturesClient` is safely closeable via `with` statement

---

## ⚠️ Assumptions

1. **Testnet only** — The base URL is hardcoded to `https://testnet.binancefuture.com`. Do not use real API keys.
2. **USDT-M Futures** — Targets USDT-margined perpetual contracts only.
3. **Quantity is in base asset** — e.g., `0.001` = 0.001 BTC for BTCUSDT.
4. **Exchange precision** — The exchange enforces LOT_SIZE and PRICE_FILTER rules. Ensure your quantity/price values conform to the symbol's tick sizes; the validator enforces a floor but not the exact step size (fetching exchange info for every trade would add latency).
5. **Environment variables** — Credentials must be in a `.env` file or exported in the shell environment before running.

---

## 🔐 Security Notes

- Never commit your `.env` file (it is in `.gitignore`).
- API signatures are redacted from log files (`signature=***`).
- Only testnet keys should be used with this bot.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `httpx` | Async-capable HTTP client with retry |
| `typer[all]` | CLI framework with automatic `--help` |
| `rich` | Beautiful terminal output |
| `python-dotenv` | `.env` file loading |
