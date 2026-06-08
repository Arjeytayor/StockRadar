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
│   └── requirements.txt
├── frontend/        ← React + Vite (web UI)
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── .github/
│   └── workflows/
│       └── ci.yml  ← GitHub Actions CI (lint + build)
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** (LTS)

### 1️⃣ Clone & Setup (first time)

```bash
git clone <repo-url>
cd StockRadar

# Python backend
cd backend
pip install -r requirements.txt

# Frontend (separate terminal)
cd frontend
npm install
```

### 2️⃣ Run the Web App

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
3. Create `backend/.env`:
```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_CHAT_ID=your-chat-id-here
```

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

## ⚠️ Important

- **NOT FINANCIAL ADVICE.** For educational purposes only.
- Backend fetches live data from Yahoo Finance — initial scan can take **2–5 minutes**.
- For production deployment, host the FastAPI backend on **Render, Railway, or AWS** and change the `API_URL` in `frontend/src/App.jsx`.

---

## 📜 License

Personal screening tool. Not financial advice.
