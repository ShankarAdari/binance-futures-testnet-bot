# ⚡ Binance Futures Testnet Trading Bot

> A **production-grade** CLI trading bot for **Binance USDT-M Futures Testnet**.
> Supports MARKET, LIMIT, STOP_MARKET, and STOP_LIMIT orders with a full Risk Management layer, plug-and-play Strategy engine, mock Backtester, and a glassmorphism web UI.

[![CI](https://github.com/ShankarAdari/binance-futures-testnet-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/ShankarAdari/binance-futures-testnet-bot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---
## 📋 Project Overview

This is not a script — it is a **mini production trading system** designed to demonstrate:

- **Backend engineering excellence** — layered architecture, strict separation of concerns, typed interfaces
- **Real-world robustness** — HMAC-SHA256 signing, exponential-backoff retry, structured logging, custom exception hierarchy
- **Extensibility** — plug-and-play strategy registry, config-driven risk limits, Dependency Injection-ready design
- **Operational readiness** — Docker support, GitHub Actions CI, PEP8 compliance, 77-test suite with mocks

**Live Demo UI:** https://shankaradari.github.io/binance-futures-testnet-bot/

---
## ✨ Features

### Core (Mandatory)
| Feature | Detail |
|---|---|
| MARKET orders | BUY / SELL — instant fill simulation |
| LIMIT orders | BUY / SELL with price resting |
| STOP_MARKET | Triggered stop loss/take profit |
| STOP_LIMIT | Stop price triggers limit entry |
| CLI (Typer + Rich) | 6 commands, neon Retro-Futuristic theme |
| Input validation | Symbol, side, type, qty, price — Decimal precision |
| Structured logging | Rotating file logs + console — requests, responses, errors |
| Error handling | Full custom exception hierarchy |
| README + examples | This file |

### Bonus
| Feature | Detail |
|---|---|
| 🔥 Risk Management | Max position size, daily loss cap, total exposure ceiling |
| 🔥 Strategy Layer | Moving Average Crossover, RSI, Combined — plug-and-play registry |
| 🔥 Backtesting Mode | Bar-by-bar mock backtest with PnL, win rate, fee simulation |
| 🔥 Glassmorphism UI | Interactive web dashboard — live at GitHub Pages |
| 🐳 Docker Support | Production Dockerfile with non-root user |
| ⚙️ CI/CD | GitHub Actions — 3 Python versions, coverage, lint, Docker build |
| 🔑 Config-driven | All limits/parameters from `.env` — zero code changes needed |

---

## 🏗️ Architecture

```
trading_bot/
├── core/
│   ├── config.py        # Typed Settings dataclass (reads .env)
│   └── constants.py     # Enums: OrderType, OrderSide, SignalDirection…
│
├── bot/
│   ├── client.py        # Binance REST API — HMAC signing, retry, redacted logs
│   ├── orders.py        # OrderManager + OrderResult DTO
│   ├── validators.py    # Fail-fast validation — Decimal precision
│   ├── risk.py          # RiskManager — position size / daily cap / exposure
│   ├── strategies.py    # MA Crossover, RSI, Combined + backtest runner
│   ├── exceptions.py    # Custom exception hierarchy (BotError → APIError …)
│   └── logging_config.py# Rotating file + console handlers
│
├── cli.py               # Typer CLI — 6 commands, Rich neon UI
├── demo.html / index.html  # Glassmorphism interactive UI
│
├── tests/
│   ├── test_validators.py    # 35 tests — all validation paths
│   ├── test_risk.py          # 15 tests — risk checks + fill recording
│   ├── test_strategies.py    # 18 tests — signals, backtest, registry
│   └── test_client_mock.py   #  9 tests — mocked HTTP (no real network)
│
├── .github/workflows/ci.yml  # GitHub Actions CI
├── Dockerfile                # Production container
├── requirements.txt
└── .env.example
```
### Data Flow
```
CLI Command
    │
    ▼
OrderValidator.validate()   ← Fail fast, Decimal precision
    │
    ▼
RiskManager.check()         ← Position size / daily cap / exposure
    │
    ▼
OrderManager.place()        ← Coordinates validate → execute → parse
    │
    ▼
BinanceFuturesClient        ← HMAC sign → HTTP POST → retry → parse
    │
    ▼
Binance Futures Testnet API
```

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+
- Binance Testnet account: https://testnet.binancefuture.com
- Git

### 1. Clone & install

```powershell
git clone https://github.com/ShankarAdari/binance-futures-testnet-bot.git
cd binance-futures-testnet-bot

python -m venv .venv
.venv\Scripts\Activate.ps1         # Windows
# or: source .venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
```

### 2. Configure credentials

```powershell
copy .env.example .env
```

Edit `.env`:
```env
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here

# Optional risk overrides
MAX_POSITION_USDT=1000.0
DAILY_LOSS_CAP_USDT=200.0
MAX_EXPOSURE_USDT=5000.0

# Optional strategy tuning
DEFAULT_STRATEGY=moving_average
MA_FAST_PERIOD=9
MA_SLOW_PERIOD=21
RSI_PERIOD=14
RSI_OVERBOUGHT=70
RSI_OVERSOLD=30
```

### 3. Docker (alternative)

```bash
docker build -t binance-futures-bot .
docker run --env-file .env binance-futures-bot place-order \
  --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## 💻 CLI Commands

### Show help
```powershell
python cli.py --help
```

### Place MARKET order
```powershell
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

### Place LIMIT order
```powershell
python cli.py place-order --symbol ETHUSDT --side SELL --type LIMIT --qty 0.1 --price 3500
```

### Place STOP_LIMIT order
```powershell
python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_LIMIT --qty 0.001 --price 57500 --stop-price 58000
```

### Check live price
```powershell
python cli.py price --symbol BTCUSDT
```

### View risk exposure
```powershell
python cli.py risk-report
```

### Run strategy signal
```powershell
python cli.py strategy --name rsi --symbol BTCUSDT
python cli.py strategy --name moving_average --symbol ETHUSDT
python cli.py strategy --name combined --symbol BTCUSDT
```

### Run mock backtest
```powershell
python cli.py backtest --strategy rsi
python cli.py backtest --strategy moving_average
```

### Interactive mode
```powershell
python cli.py place-order --interactive
```

---

## 📊 Example Order Output

```
╔══════════════════════════════════════╗
║     ORDER SUMMARY                    ║
╚══════════════════════════════════════╝
  Symbol   : BTCUSDT
  Side     : BUY
  Type     : LIMIT
  Quantity : 0.001
  Price    : 60000

╔══════════════════════════════════════╗
║     RESPONSE                         ║
╚══════════════════════════════════════╝
  Order ID   : 4561234567
  Status     : NEW
  Exec. Qty  : 0.000
  Avg Price  : 0.00

✅ Order placed successfully
```

---

## 📝 Logs Sample

```
2026-05-04 23:15:01,234 | INFO     | bot.client   | BinanceFuturesClient initialised — endpoint: https://testnet.binancefuture.com
2026-05-04 23:15:01,235 | DEBUG    | bot.client   | → POST /fapi/v1/order  params={'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'LIMIT', 'quantity': '0.001', 'price': '60000', 'timeInForce': 'GTC', 'timestamp': 1714863301235, 'recvWindow': 5000, 'signature': '***'}
2026-05-04 23:15:01,891 | DEBUG    | bot.client   | ← POST /fapi/v1/order  status=200  body={"orderId":4561234567,"symbol":"BTCUSDT","status":"NEW",...}
2026-05-04 23:15:01,892 | INFO     | bot.client   | Order accepted — orderId=4561234567 status=NEW
2026-05-04 23:15:01,893 | INFO     | bot.risk     | Risk check PASSED for BUY BTCUSDT qty=0.001000
```

---

## 🧪 Testing

```powershell
# Run all 77 tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=bot --cov=core --cov-report=term-missing

# Single module
python -m pytest tests/test_validators.py -v
python -m pytest tests/test_risk.py -v
python -m pytest tests/test_strategies.py -v
python -m pytest tests/test_client_mock.py -v
```

**Test Results:** `77 passed in 7.99s` ✅

| Module | Tests | Coverage |
|---|---|---|
| `bot/validators.py` | 35 | Symbol, side, type, qty, price, edge cases |
| `bot/risk.py` | 15 | Position size, daily cap, exposure, fills |
| `bot/strategies.py` | 18 | MA, RSI, combined, backtest, registry |
| `bot/client.py` | 9 | Mocked HTTP — market, limit, errors |

---

## 🔮 Future Improvements

- WebSocket price feed for real-time order book data
- OCO (One-Cancels-Other) order type
- Database persistence for trade history (SQLite/PostgreSQL)
- Telegram / Discord alerting on fills and risk breaches
- Paper trading mode with real-time testnet price feeds
- Portfolio-level risk management across multiple symbols
- Machine learning signal generation (LSTM price prediction)

---

## 📄 License

MIT — free to use, modify, and distribute.
