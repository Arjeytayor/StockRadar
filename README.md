# 📊 StockRadar

> **Status:** Web app (localhost) and Telegram bot fully functional.

Stock & Crypto screening, scoring, and analysis — runs on your local machine.

---

## 🏗️ Architecture

```
StockRadar/
├── backend/         ← FastAPI (Python) — screener logic + Telegram
│   ├── main.py
│   ├── scoring.py
│   ├── screener.py
│   ├── backtest.py
│   ├── telegram_alert.py
│   ├── config.py
│   ├── tests/           ← pytest suite (scoring/backtest logic)
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/        ← React + Vite (web UI)
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
├── .github/
│   └── workflows/
│       └── ci.yml  ← GitHub Actions CI (compile check + pytest + frontend build)
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** (LTS)

### 1️⃣ Clone & Setup (first time)

```bash
git clone https://github.com/Arjeytayor/StockRadar.git
cd StockRadar

# Python backend
cd backend
pip install -r requirements.txt

# Frontend (separate terminal)
cd frontend
npm install
```

### 2️⃣ Configure environment (optional)

Both apps work out of the box on localhost with no configuration. To override defaults:

**Backend** (`backend/.env`):
```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
CORS_ORIGINS=http://localhost:5173   # comma-separated list of allowed frontend origins
```

**Frontend** (`frontend/.env`, copy from `frontend/.env.example`):
```env
VITE_API_URL=http://localhost:8000
```

### 3️⃣ Run the Web App

**Terminal 1 — Backend:**
```bash
cd backend
python main.py
# → http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
# → http://localhost:5173
```

**Open your browser to:** `http://localhost:5173`

Click **🔍 Run Screener** and wait 2-5 minutes for results.

---

## 🤖 Telegram Bot

The bot sends daily/scheduled stock and crypto alerts with:
- Ranked stock/crypto picks
- Layman summaries (plain English)
- Investment projections ($1,000 → 30/90 day outlook)
- Scores, P/E, RSI, moving average signals

### Setup (one-time)

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get your `BOT_TOKEN` and `CHAT_ID`
3. Add them to `backend/.env` as shown in [Configure environment](#2️⃣-configure-environment-optional)

### Usage

```bash
cd backend
python screener.py              # Stocks + Crypto + Telegram alert
python screener.py --no-crypto  # Stocks only
python screener.py --no-telegram # Skip Telegram, just see results
```

---

## 🔌 API

`POST http://localhost:8000/api/screen`

```json
{
  "watchlist": "default",   // "default" | "sp500" | "crypto"
  "top": 5,
  "include_crypto": true
}
```

Returns ranked array with fields: `ticker`, `company`, `sector`, `total_score`, `pe`, `rsi`, `ma_signal`, `verdict`, `layman_summary`, `investment_30d`, `investment_90d`.

---

## 📋 How to Use

| Mode | What to do |
|------|-----------|
| **Web UI** (`npm run dev`) | Open browser, click "Run Screener", view cards |
| **CLI + Telegram** | `python screener.py` — runs, then sends Telegram |
| **CLI only** | `python screener.py --no-telegram` |
| **Stocks only** | `python screener.py --no-crypto` |

---

## 🧪 Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Covers the pure scoring/screening/backtest logic in `scoring.py` and `backtest.py` — no network calls, no API keys required. CI runs this suite on every push and PR.

---

## ⚠️ Important

- **NOT FINANCIAL ADVICE.** For educational purposes only.
- Backend fetches live data from Yahoo Finance — initial scan can take **2–5 minutes**.
- For production deployment, host the FastAPI backend on **Render, Railway, or AWS**, then set `VITE_API_URL` (frontend) and `CORS_ORIGINS` (backend) to match — no code changes needed.

---

## 📜 License

MIT — see [LICENSE](LICENSE).
