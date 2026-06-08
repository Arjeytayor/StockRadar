"""
backtest.py
Handles backtesting: compare each top stock's 3-month return to SPY.
"""

import logging
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_three_month_return(ticker: str) -> float:
    """
    Fetch the 3-month total return for a given ticker.
    Returns the percentage return (e.g., 0.05 for 5%).
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo")
        if hist.empty or len(hist) < 2:
            return 0.0
        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        if start_price == 0:
            return 0.0
        return (end_price - start_price) / start_price
    except Exception as exc:
        logger.error(f"Failed to fetch 3-month return for {ticker}: {exc}")
        return 0.0


def compare_to_market(ticker_return: float, spy_return: float) -> str:
    """
    Compare a stock's return to the SPY return.
    Returns a label: "Beat market", "Matched market", or "Underperformed market".
    """
    diff = ticker_return - spy_return
    if diff > 0.01:
        return "Beat market"
    elif diff < -0.01:
        return "Underperformed market"
    else:
        return "Matched market"


def run_backtest(ticker: str) -> dict:
    """
    Run a 3-month backtest for a single stock.
    Returns a dict with ticker, stock_return, spy_return, difference, and label.
    """
    stock_return = fetch_three_month_return(ticker)
    spy_return = fetch_three_month_return("SPY")
    label = compare_to_market(stock_return, spy_return)

    return {
        "ticker": ticker,
        "stock_return": round(stock_return * 100, 2),  # as percentage
        "spy_return": round(spy_return * 100, 2),
        "difference": round((stock_return - spy_return) * 100, 2),
        "label": label,
    }
