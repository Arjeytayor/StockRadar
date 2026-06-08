"""
screener.py
Main script that orchestrates screening, scoring, backtesting, and alerts.

# Commands for Windows:
# cd C:/Users/DELL/Documents/StockRadar
# pip install -r requirements.txt
# python screener.py
# python screener.py --no-telegram
# python screener.py --sector tech --top 3
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import yfinance as yf
import pandas as pd
import schedule

from config import Weights
from scoring import (
    DEFAULT_WATCHLIST,
    CRYPTO_WATCHLIST,
    SECTOR_MAP,
    fetch_sp500_tickers,
    fetch_stock_data,
    passes_screen,
    score_fundamentals,
    score_technicals,
    score_momentum,
    get_verdict,
    generate_summary,
    get_ma_signal,
    get_volume_signal,
    fetch_crypto_data,
    passes_crypto_screen,
    score_crypto_technicals,
    score_crypto_momentum,
    generate_layman_summary,
    investment_projection,
)
from backtest import run_backtest
from telegram_alert import format_telegram_message, send_telegram_alert

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("C:/Users/DELL/Documents/StockRadar/errors.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main screener logic
# ---------------------------------------------------------------------------
def run_screen(
    watchlist: list,
    sector_filter: str = None,
    top_n: int = 5,
    skip_telegram: bool = False,
    backtest_only: bool = False,
    include_crypto: bool = True,
):
    """
    Run the full screening, scoring, and alert pipeline for stocks and optional crypto.
    """
    # ------------------------------------------------------------
    # 1. Stock pipeline
    # ------------------------------------------------------------
    logger.info("Fetching SPY historical data for momentum benchmarking...")
    try:
        spy_ticker = yf.Ticker("SPY")
        spy_hist = spy_ticker.history(period="6mo")
    except Exception as exc:
        logger.error(f"Failed to fetch SPY data: {exc}")
        spy_hist = None

    all_data = []
    failed_tickers = []
    for ticker in watchlist:
        data = fetch_stock_data(ticker)
        if data is None:
            failed_tickers.append(ticker)
            continue
        all_data.append(data)

    if failed_tickers:
        logger.warning(f"Failed tickers (will be skipped): {failed_tickers}")

    # Compute sector average P/E for fundamental scoring
    sector_pe = {}
    for s, sector in SECTOR_MAP.items():
        if sector not in sector_pe:
            sector_pe[sector] = []
    for data in all_data:
        t = data["ticker"]
        sector = SECTOR_MAP.get(t)
        pe = data.get("pe_ratio")
        if sector and pe and not pd.isna(pe):
            sector_pe[sector].append(pe)
    sector_avg_pe = {
        sector: sum(vals) / len(vals) if vals else None
        for sector, vals in sector_pe.items()
    }

    scored_stocks = []
    for data in all_data:
        if not passes_screen(data):
            continue

        ticker = data["ticker"]
        sector = SECTOR_MAP.get(ticker, "Unknown")

        # Apply sector filter if requested
        if sector_filter and sector != sector_filter.lower().replace(" ", "_"):
            continue

        f_score = score_fundamentals(data, sector_avg_pe)
        t_score = score_technicals(data)
        m_score = score_momentum(data, spy_hist)

        total = (
            f_score * Weights.FUNDAMENTALS
            + t_score * Weights.TECHNICALS
            + m_score * Weights.MOMENTUM
        )

        # Layman summary and investment projection
        layman = generate_layman_summary(data, total, ticker_type="stock")
        proj_30 = investment_projection(data, total, timeframe_days=30)
        proj_90 = investment_projection(data, total, timeframe_days=90)

        scored_stocks.append(
            {
                "ticker": ticker,
                "company": data["info"].get("longName", ticker),
                "sector": sector.replace("_", " ").title(),
                "type": "stock",
                "current_price": data["current_price"],
                "total_score": total,
                "pe": data["pe_ratio"] if data["pe_ratio"] is not None else float("nan"),
                "rsi": data["hist"]["RSI"].iloc[-1],
                "ma_signal": get_ma_signal(data),
                "volume_signal": get_volume_signal(data),
                "verdict": get_verdict(total),
                "data": data,
                "summary": generate_summary(data, total),
                "layman_summary": layman,
                "investment_30d": proj_30,
                "investment_90d": proj_90,
            }
        )

    # ------------------------------------------------------------
    # 2. Crypto pipeline
    # ------------------------------------------------------------
    scored_crypto = []
    if include_crypto and not backtest_only:
        logger.info("Fetching crypto market data...")
        try:
            btc_ticker = yf.Ticker("BTC-USD")
            btc_hist = btc_ticker.history(period="6mo")
        except Exception as exc:
            logger.error(f"Failed to fetch BTC data: {exc}")
            btc_hist = None

        for ticker in CRYPTO_WATCHLIST:
            data = fetch_crypto_data(ticker)
            if data is None:
                continue
            if not passes_crypto_screen(data):
                continue

            t_score = score_crypto_technicals(data)
            m_score = score_crypto_momentum(data, btc_hist)
            # Crypto weights: 0% fundamentals, 60% technicals, 40% momentum
            total = t_score * 0.60 + m_score * 0.40

            layman = generate_layman_summary(data, total, ticker_type="crypto")
            proj_30 = investment_projection(data, total, timeframe_days=30)
            proj_90 = investment_projection(data, total, timeframe_days=90)

            scored_crypto.append(
                {
                    "ticker": ticker.replace("-USD", ""),
                    "company": data["info"].get("longName", ticker.replace("-USD", "")),
                    "sector": "Crypto",
                    "type": "crypto",
                    "current_price": data["current_price"],
                    "total_score": total,
                    "pe": float("nan"),
                    "rsi": data["hist"]["RSI"].iloc[-1],
                    "ma_signal": get_ma_signal(data),
                    "volume_signal": get_volume_signal(data),
                    "verdict": get_verdict(total),
                    "data": data,
                    "summary": f"Crypto momentum score: {total:.1f}/100",
                    "layman_summary": layman,
                    "investment_30d": proj_30,
                    "investment_90d": proj_90,
                }
            )

    # Combine and rank all results
    all_scored = scored_stocks + scored_crypto
    all_scored.sort(key=lambda x: x["total_score"], reverse=True)

    # ------------------------------------------------------------
    # 3. Console output
    # ------------------------------------------------------------
    print("\n" + "=" * 100)
    print(f"{'Rank':<6}{'Ticker':<8}{'Name':<25}{'Sector':<18}{'Type':>8}{'Price':>10}{'Score':>8}{'P/E':>8}{'RSI':>8} {'MA Signal':<30}{'Volume Signal':<20}{'Verdict':<20}")
    print("=" * 100)
    for rank, r in enumerate(all_scored[:top_n], start=1):
        ticker_type = r.get("type", "stock")
        print(
            f"{rank:<6}{r['ticker']:<8}{r['company'][:24]:<25}{r['sector']:<18}"
            f"{ticker_type:>8} "
            f"${r['current_price']:>8.2f}{r['total_score']:>7.1f}{r['pe']:>7.1f}{r['rsi']:>7.1f}  "
            f"{r['ma_signal']:<28}  {r['volume_signal']:<18}  {r['verdict']:<20}"
        )
    print("=" * 100)

    # Top 5 summaries with layman explanations
    print("\n--- Top Picks Summary (Layman-friendly) ---\n")
    for i, r in enumerate(all_scored[:5], start=1):
        print(f"{i}. {r['ticker']} ({r.get('type', 'stock').upper()}) — {r['summary']}")
        print(f"   📖 Layman: {r['layman_summary']}")
        print(f"   💰 If you invested $1,000 today: ~${r['investment_30d']['projected_value']} in 30 days, ~${r['investment_90d']['projected_value']} in 90 days")
        print()

    # Backtest (stocks only)
    if not backtest_only:
        stock_results = [r for r in all_scored[:5] if r.get("type") == "stock"]
        if stock_results:
            print("\n--- 3-Month Backtest (vs SPY) ---\n")
            for r in stock_results:
                bt = run_backtest(r["ticker"])
                print(
                    f"{bt['ticker']}: {bt['stock_return']:.2f}% (SPY: {bt['spy_return']:.2f}%) "
                    f"— {bt['label']} (diff: {bt['difference']:+.2f}%)"
                )

    # Save to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    csv_name = f"screener_results_{timestamp}.csv"
    try:
        df = pd.DataFrame(all_scored)
        # Keep only relevant columns for CSV
        df = df[["ticker", "company", "sector", "type", "current_price", "total_score", "pe", "rsi", "ma_signal", "volume_signal", "verdict", "summary"]]
        df.to_csv(csv_name, index=False)
        logger.info(f"Results saved to {csv_name}")
    except Exception as exc:
        logger.error(f"Failed to save CSV: {exc}")

    # Telegram alert
    if not skip_telegram and not backtest_only:
        message = format_telegram_message(all_scored, top_n=top_n)
        send_telegram_alert(message)

    return all_scored


def run_scheduler(watchlist: list, top_n: int = 5, skip_telegram: bool = False):
    """
    Schedule the screener to run every weekday at 8:00 AM.
    """
    import datetime as dt

    def job():
        now = dt.datetime.now()
        # Skip weekends
        if now.weekday() >= 5:
            logger.info("Weekend detected, skipping run.")
            return
        logger.info("Running scheduled daily screener...")
        run_screen(watchlist, top_n=top_n, skip_telegram=skip_telegram)

    schedule.every().monday.at("08:00").do(job)
    schedule.every().tuesday.at("08:00").do(job)
    schedule.every().wednesday.at("08:00").do(job)
    schedule.every().thursday.at("08:00").do(job)
    schedule.every().friday.at("08:00").do(job)

    logger.info("Scheduler started. Waiting for 8:00 AM on weekdays...")
    while True:
        schedule.run_pending()
        time.sleep(60)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="StockRadar — Stock Screening, Scoring and Alert System")
    parser.add_argument("--sector", type=str, default=None, help="Filter by sector (e.g., tech, healthcare)")
    parser.add_argument("--top", type=int, default=5, help="Number of results to show (default: 5)")
    parser.add_argument("--watchlist", type=str, default="default", choices=["default", "sp500", "crypto"], help="Watchlist to use (default, sp500, or crypto-only)")
    parser.add_argument("--no-crypto", action="store_true", help="Skip crypto analysis")
    parser.add_argument("--no-telegram", action="store_true", help="Run without sending Telegram message")
    parser.add_argument("--backtest", action="store_true", help="Run backtest only")
    parser.add_argument("--schedule", action="store_true", help="Run scheduler for daily alerts at 8:00 AM weekdays")

    args = parser.parse_args()

    # Build watchlist
    if args.watchlist == "sp500":
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        tickers = fetch_sp500_tickers()
        include_crypto = not args.no_crypto
    elif args.watchlist == "crypto":
        tickers = []
        include_crypto = True
    else:
        tickers = DEFAULT_WATCHLIST
        include_crypto = not args.no_crypto

    # Sector filter normalization
    sector_filter = args.sector

    if args.schedule:
        run_scheduler(tickers, top_n=args.top, skip_telegram=args.no_telegram)
    else:
        run_screen(
            tickers,
            sector_filter=sector_filter,
            top_n=args.top,
            skip_telegram=args.no_telegram,
            backtest_only=args.backtest,
            include_crypto=include_crypto,
        )


if __name__ == "__main__":
    main()
