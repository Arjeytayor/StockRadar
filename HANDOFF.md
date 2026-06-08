# StockRadar — Session Hand-Off

> **Date:** 2026-06-08
> **Status:** Web app (localhost:5173) working with professional dark theme. Telegram alerts working. Mobile code archived (see `_ARCHIVE/`).
>
> **Focus:** Web (localhost) + Telegram only. Mobile de-prioritized.

---

## What Was Built

### 1. CLI Screener (`backend/screener.py`) — ✅ WORKING
- Screens stocks from `DEFAULT_WATCHLIST` or S&P 500
- Screens crypto from `CRYPTO_WATCHLIST` (BTC, ETH, SOL, ADA, XRP, AVAX, DOT, LINK, DOGE, MATIC)
- Outputs ranked results with scores, P/E, RSI, MA signal, volume signal, verdict
- Includes backtest vs SPY
- Saves results to CSV
- Sends Telegram alerts with layman summaries and investment projections

### 2. Core Scoring Engine (`backend/scoring.py`) — ✅ WORKING
- `fetch_stock_data()` — fetches 1 year of data (needed for 200-day MA)
- `fetch_crypto_data()` — fetches 1 year of crypto data
- `passes_screen()` / `passes_crypto_screen()` — screening gates
- `score_fundamentals()` / `score_technicals()` / `score_momentum()` — scoring
- `generate_layman_summary()` — plain-English explanations
- `investment_projection()` — $1,000 → projected value in 30/90 days
- `get_ma_signal()` / `get_volume_signal()` — signal generators

### 3. Telegram Alerts (`backend/telegram_alert.py`) — ✅ WORKING
- Formats stocks and crypto separately
- Includes layman summaries
- Includes investment projections
- Has prominent "NOT FINANCIAL ADVICE" disclaimer

### 4. FastAPI Backend (`backend/main.py`) — ✅ WORKING
- `POST /api/screen` — runs the full pipeline, returns JSON
- CORS enabled for localhost:5173
- Tested and returns proper JSON with all fields

### 5. React Frontend (`frontend/`) — ✅ WORKING
- `App.jsx` — professional dark theme with loading skeleton, error handling, defensive rendering
- Form controls: watchlist, topN, includeCrypto
- Displays results as ranked cards with stats, signals, verdict, summary, and projections
- Errors displayed gracefully (no blank pages)
- `npm run build` succeeds

### 6. Mobile — 🗄️ ARCHIVED
- Moved to `_ARCHIVE/mobile/`
- Can be revisited when resources (Android Studio/Xcode) are available
- Capacitor config file preserved in archive

---

## Project Structure

```
StockRadar/
├── backend/
│   ├── main.py              ← FastAPI server (POST /api/screen)
│   ├── screener.py          ← CLI entry point
│   ├── scoring.py           ← Core screening/scoring logic
│   ├── backtest.py          ← Backtesting vs SPY
│   ├── telegram_alert.py    ← Telegram bot formatting + sending
│   ├── config.py            ← API keys (via .env), weights, constants
│   └── requirements.txt     ← Python deps (FastAPI, uvicorn, yfinance, pandas)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          ← React UI (professional dark theme)
│   │   ├── main.jsx         ← Entry point
│   │   └── index.css        ← Dark theme styles with animations
│   ├── index.html           ← HTML template
│   ├── package.json         ← React + Vite deps
│   └── vite.config.js       ← Vite config with proxy to :8000
├── .github/workflows/
│   └── ci.yml               ← GitHub Actions (lint + build)
├── .gitignore               ← Ignores cache, node_modules, CSVs, secrets (.env)
├── HANDOFF.md               ← This file
├── README.md                ← How to use web + Telegram
└── _ARCHIVE/
    └── mobile/              ← Capacitor mobile code (archived)
```

---

## How to Use

### Web App (Frontend):
```bash
# Terminal 1 — Backend
cd backend
python main.py

# Terminal 2 — Frontend
cd frontend
npm install      # first time only
npm run dev      # → http://localhost:5173
```

### Telegram (CLI Mode):
```bash
cd backend
python screener.py              # stocks + crypto + Telegram alert
python screener.py --no-crypto  # stocks only
python screener.py --no-telegram # skip Telegram
```

---

## API Test

```bash
curl -X POST http://127.0.0.1:8000/api/screen \
  -H "Content-Type: application/json" \
  -d '{"watchlist":"default","top":3,"include_crypto":true}'
```

---

## 🎯 Long-Term Vision: x100 / x1000 Outlier Detection (Future Roadmap)

> **Goal:** Evolve StockRadar from a standard screener into a tool that spots extreme asymmetric opportunities — stocks or crypto where a small investment ($10) could theoretically return **x100 or x1000** returns.

### What this means:
- **Not about short-term trading:** Focus on *catalyst-driven, asymmetric opportunities* — small, under-the-radar stocks or crypto whose fundamentals + news + on-chain/social signals suggest explosive, game-changing potential.
- **Key research vectors to add:**
  - **Early-stage fundamentals:** Revenue growth > 200%, user growth, network effects, low float, concentrated insider ownership
  - **News & sentiment scanning:** NLP analysis of news, SEC filings, social media (Reddit, X/Twitter) for early signals before mainstream attention
  - **On-chain metrics (crypto):** Wallet growth, active addresses, developer activity, exchange flow, token unlock schedules
  - **Option flow & unusual volume (stocks):** Options activity, dark pool data, short-interest anomalies
  - **Market structure signals:** Low market cap vs. TAM, recently listed/SPAC/delist-relist potential, regulatory catalysts

### When this gets built:
- After the current web app + Telegram bot are stable and in daily use
- Requires data sources: news APIs (NewsAPI, Reddit, X), on-chain APIs (Dune, Etherscan), options flow APIs (OpenBB, Polygon)
- Start with a separate `outlier/` module and run alongside the existing screener
- Track hits/false-positives in a simple database to learn and improve scoring over time

---

## Next Session Priorities

1. ✅ Web UI tested and working
2. ✅ Defensive rendering / error handling (no blank pages)
3. ✅ `.gitignore` excludes secrets (`.env` ignored)
4. ✅ Clean committed history on GitHub
5. 🟡 (Future) Begin `outlier/` module scoping for x100/x1000 vision
6. 🟡 (Future) Deploy backend to cloud (Render/Railway) for remote access
