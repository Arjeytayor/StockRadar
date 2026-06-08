# StockRadar — Project Summary

## What Was Built

StockRadar is a Python stock screening, scoring, and alert system that identifies stocks with good prospects during a market downturn and sends a daily Telegram message with the top picks.

---

## Files Created

### Core Scripts

| File | Size (approx) | Purpose |
|------|--------------|---------|
| `screener.py` | ~260 lines | Main script — CLI entry point, orchestrates screening, scoring, backtesting, and alerts. Includes a weekday scheduler at 8:00 AM. |
| `scoring.py` | ~440 lines | Screening rules and 3-dimension scoring engine (Fundamentals 40%, Technicals 40%, Momentum 20%). |
| `backtest.py` | ~55 lines | 3-month backtest logic — compares each top stock's return to SPY (S&P 500 ETF). |
| `telegram_alert.py` | ~90 lines | Telegram message formatting and sending via Bot API. |
| `config.py` | ~35 lines | Loads environment variables from `.env` and stores screening thresholds / scoring weights. |

### Configuration / Support

| File | Purpose |
|------|---------|
| `.env` | Credential template for Telegram. Never share this file. |
| `requirements.txt` | Lists all required Python libraries (yfinance, pandas, numpy, python-dotenv, requests, schedule, lxml). |
| `errors.log` | Auto-created at runtime to log errors and skipped tickers. |
| `PROJECT_SUMMARY.md` | This file. |

---

## Key Features Implemented

### PART 1 — Data Source
- Uses `yfinance` to pull live and historical stock data.
- Default watchlist: 30 well-known US stocks across 6 sectors (tech, energy, healthcare, financials, consumer staples, industrials).
- Optional `--watchlist sp500` flag scrapes the full S&P 500 ticker list from Wikipedia using pandas.

### PART 2 — Screening
- Filters out stocks with negative/missing revenue growth.
- Filters out stocks with P/E above 35 or missing.
- Filters out stocks with Debt-to-Equity above 2.0.
- Filters out stocks with average daily volume below 500,000.
- Filters out stocks with price below $5.

### PART 3 — Scoring System (0–100)
Three dimensions:
- **Fundamentals (40%)**: P/E vs sector average, revenue growth YoY, profit margin, debt-to-equity.
- **Technical Signals (40%)**: RSI (30-55 scores highest), price vs 50/200-day MAs, volume spike vs 30-day avg, MACD bullish crossover.
- **Momentum (20%)**: 1-month and 3-month price change relative to SPY.

### PART 4 — Output
- Prints a ranked table with: Rank, Ticker, Name, Sector, Price, Score, P/E, RSI, MA Signal, Volume Signal, Verdict.
- Verdict categories: Strong buy candidate (75+), Watch closely (55-74), Neutral (35-54), Avoid (<35).
- Top 5 get a 2-3 sentence plain-English summary with real numbers.
- Full results saved to `screener_results_YYYY-MM-DD_HH-MM.csv`.

### PART 5 — Backtest
- For each top-5 stock, calculates 3-month return vs SPY over the same period.
- Labels: "Beat market", "Matched market", or "Underperformed market".
- Triggered with `--backtest` or runs automatically as part of the full pipeline.

### PART 6 — Telegram Daily Alert
- Formatted daily message with date, market mood (based on SPY 5-day trend), and top 5 picks with scores, prices, P/E, RSI, and summary.
- Setup instructions embedded in `.env` file comments.
- Scheduled for 8:00 AM weekdays via python-schedule, skipping weekends automatically.

### PART 7 — Command Line Flags
- `--sector healthcare` — filter by sector
- `--top 10` — change number of results shown
- `--watchlist sp500` — screen the full S&P 500
- `--no-telegram` — run without sending Telegram message
- `--backtest` — run backtest only
- `--schedule` — start the daily weekday scheduler

### PART 8 — Project Structure
All files saved to: `C:\Users\DELL\Documents\StockRadar\`
- `screener.py` — main script and scheduler
- `scoring.py` — scoring and screening logic
- `telegram_alert.py` — Telegram formatting and sending
- `backtest.py` — backtest logic
- `config.py` — loads environment variables and settings
- `.env` — credentials template (reminder: never share)
- `requirements.txt` — all required libraries
- `errors.log` — created automatically at runtime

### PART 9 — Error Handling
- Failed tickers: skipped and logged to `errors.log`.
- Failed Telegram sends: error printed, script continues.
- Missing data fields: stock skipped from scoring.
- yfinance failures: retry once after 3 seconds, then skip.

---

## How to Run

```cmd
cd C:\Users\DELL\Documents\StockRadar
pip install -r requirements.txt
python screener.py
python screener.py --no-telegram
python screener.py --sector tech --top 3
python screener.py --watchlist sp500 --top 10
python screener.py --backtest
python screener.py --schedule
```

---

## Tech Stack
- Python 3.11+
- yfinance (Yahoo Finance data)
- pandas (data manipulation, S&P 500 scraping)
- numpy (numerical operations)
- python-dotenv (environment variables)
- requests (Telegram API)
- schedule (daily cron-like scheduling)
- lxml (HTML table parsing for S&P 500)

---

## Notes
- All comments in the code are in plain English.
- The scoring system is designed to reward value/momentum plays — **this is not financial advice**.
- Run time for the default 30-stock watchlist is under 1 minute.
- Run time for the S&P 500 watchlist is approximately 20-30 minutes depending on network speed.
