"""
scoring.py
Handles screening logic and multi-dimensional scoring for stocks and crypto.
"""

import logging
import time
import numpy as np
import yfinance as yf
import pandas as pd

from config import Screening, Weights

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default watchlist
# ---------------------------------------------------------------------------
DEFAULT_WATCHLIST = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "NVDA", "META",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK",
    # Financials
    "JPM", "BAC", "GS", "WFC",
    # Consumer staples
    "PG", "KO", "PEP", "WMT", "COST",
    # Industrials
    "CAT", "HON", "GE", "BA", "MMM",
]

SECTOR_MAP = {
    "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech", "NVDA": "tech", "META": "tech",
    "XOM": "energy", "CVX": "energy", "COP": "energy", "SLB": "energy",
    "JNJ": "healthcare", "UNH": "healthcare", "PFE": "healthcare", "ABBV": "healthcare", "MRK": "healthcare",
    "JPM": "financials", "BAC": "financials", "GS": "financials", "WFC": "financials",
    "PG": "consumer_staples", "KO": "consumer_staples", "PEP": "consumer_staples", "WMT": "consumer_staples", "COST": "consumer_staples",
    "CAT": "industrials", "HON": "industrials", "GE": "industrials", "BA": "industrials", "MMM": "industrials",
}


# ---------------------------------------------------------------------------
# Crypto watchlist
# ---------------------------------------------------------------------------
CRYPTO_WATCHLIST = [
    "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "XRP-USD",
    "AVAX-USD", "DOT-USD", "LINK-USD", "DOGE-USD", "MATIC-USD",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _retry_yfinance(ticker: str) -> yf.Ticker:
    """Fetch a yfinance Ticker object with one retry on failure."""
    try:
        return yf.Ticker(ticker)
    except Exception:
        time.sleep(3)
        return yf.Ticker(ticker)


def _safe_get(info: dict, key: str, fallback=None):
    """Safely get a value from a yfinance info dict."""
    try:
        val = info.get(key, fallback)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return fallback
        return val
    except Exception:
        return fallback


def fetch_sp500_tickers():
    """Scrape the full S&P 500 ticker list from Wikipedia using pandas."""
    import requests

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(response.text)
        df = tables[0]
        return df["Symbol"].tolist()
    except Exception as exc:
        logger.error(f"Failed to fetch S&P 500 tickers: {exc}")
        return DEFAULT_WATCHLIST


def fetch_stock_data(ticker: str):
    """
    Fetch and return a dictionary with all info, historicals, and computed metrics.
    Returns None if data is insufficient.
    """
    try:
        t = _retry_yfinance(ticker)
        info = t.info or {}

        # Basic info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if current_price is None or current_price <= 0:
            return None

        pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        debt_equity = info.get("debtToEquity")
        if debt_equity is not None and debt_equity > 100:
            # yfinance sometimes gives %, normalize to ratio
            debt_equity = debt_equity / 100.0

        revenue_growth = info.get("revenueGrowth")
        profit_margin = info.get("profitMargins")

        # Volume
        avg_volume = info.get("averageVolume") or info.get("volume")

        # Historicals for technicals (need ≥200 days for MA200)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 200:
            return None

        # Moving averages
        hist["MA50"] = hist["Close"].rolling(window=50).mean()
        hist["MA200"] = hist["Close"].rolling(window=200).mean()

        # RSI calculation
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0)).abs()
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        hist["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = hist["Close"].ewm(span=12, adjust=False).mean()
        ema26 = hist["Close"].ewm(span=26, adjust=False).mean()
        hist["MACD"] = ema12 - ema26
        hist["MACD_Signal"] = hist["MACD"].ewm(span=9, adjust=False).mean()

        # Volume spike
        avg_vol_30 = hist["Volume"].tail(30).mean()
        latest_vol = hist["Volume"].iloc[-1]

        return {
            "ticker": ticker,
            "info": info,
            "current_price": current_price,
            "pe_ratio": pe_ratio,
            "debt_equity": debt_equity,
            "revenue_growth": revenue_growth,
            "profit_margin": profit_margin,
            "avg_volume": avg_volume,
            "hist": hist,
            "avg_vol_30": avg_vol_30,
            "latest_vol": latest_vol,
        }
    except Exception as exc:
        logger.error(f"Failed to fetch data for {ticker}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------
def passes_screen(data: dict) -> bool:
    """Return True if the stock meets all screening criteria."""
    if data is None:
        return False

    # Negative or missing revenue growth
    rev_growth = data.get("revenue_growth")
    if rev_growth is None or (isinstance(rev_growth, float) and np.isnan(rev_growth)) or rev_growth < 0:
        return False

    # P/E ratio above 35 or missing
    pe = data.get("pe_ratio")
    if pe is None or (isinstance(pe, float) and np.isnan(pe)) or pe > Screening.MAX_PE:
        return False

    # Debt-to-equity above 2.0
    de = data.get("debt_equity")
    if de is None or (isinstance(de, float) and np.isnan(de)) or de > Screening.MAX_DEBT_TO_EQUITY:
        return False

    # Average daily volume below 500,000
    vol = data.get("avg_volume")
    if vol is None or (isinstance(vol, float) and np.isnan(vol)) or vol < Screening.MIN_AVG_DAILY_VOLUME:
        return False

    # Price below $5
    if data["current_price"] < Screening.MIN_PRICE:
        return False

    return True


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_fundamentals(data: dict, sector_avg_pe: dict) -> float:
    """Score fundamentals on a 0-100 scale."""
    score = 0.0
    pe = data.get("pe_ratio")
    rev = data.get("revenue_growth")
    pm = data.get("profit_margin")
    de = data.get("debt_equity")

    # P/E vs sector average (lower is better) -- up to 40 pts
    sector = SECTOR_MAP.get(data["ticker"], "unknown")
    avg_pe = sector_avg_pe.get(sector, pe)
    if pe and avg_pe and avg_pe > 0:
        ratio = pe / avg_pe
        if ratio <= 0.5:
            score += 40
        elif ratio <= 0.75:
            score += 30
        elif ratio <= 1.0:
            score += 20
        elif ratio <= 1.25:
            score += 10
        else:
            score += 5

    # Revenue growth -- up to 30 pts
    if rev is not None and not np.isnan(rev):
        pct = rev * 100
        if pct >= 20:
            score += 30
        elif pct >= 10:
            score += 25
        elif pct >= 5:
            score += 20
        elif pct >= 2:
            score += 15
        elif pct >= 0:
            score += 10

    # Profit margin -- up to 20 pts
    if pm is not None and not np.isnan(pm):
        pct = pm * 100
        if pct >= 20:
            score += 20
        elif pct >= 10:
            score += 15
        elif pct >= 5:
            score += 10
        elif pct >= 0:
            score += 5

    # Debt-to-equity -- up to 10 pts (lower is better)
    if de is not None and not np.isnan(de):
        if de <= 0.3:
            score += 10
        elif de <= 0.6:
            score += 8
        elif de <= 1.0:
            score += 5
        elif de <= 1.5:
            score += 3
        else:
            score += 1

    return min(score, 100.0)


def score_technicals(data: dict) -> float:
    """Score technical signals on a 0-100 scale."""
    score = 0.0
    hist = data["hist"]
    rsi = hist["RSI"].iloc[-1]
    macd = hist["MACD"].iloc[-1]
    macd_sig = hist["MACD_Signal"].iloc[-1]
    price = data["current_price"]
    ma50 = hist["MA50"].iloc[-1]
    ma200 = hist["MA200"].iloc[-1]

    # RSI between 30 and 55 scores highest -- up to 30 pts
    if pd.notna(rsi):
        if 30 <= rsi <= 55:
            score += 30
        elif rsi < 30:
            score += 20
        elif rsi <= 70:
            score += 15
        else:
            score += 5

    # Price vs 50-day and 200-day MAs -- up to 30 pts
    if pd.notna(ma50) and pd.notna(ma200):
        if price > ma50 > ma200:
            score += 30
        elif price > ma50 and price > ma200:
            score += 20
        elif price > ma200:
            score += 15
        elif price > ma50:
            score += 10
        else:
            score += 5

    # Volume spike vs 30-day average -- up to 20 pts
    if data["avg_vol_30"] and data["avg_vol_30"] > 0:
        ratio = data["latest_vol"] / data["avg_vol_30"]
        if ratio >= 1.5:
            score += 20
        elif ratio >= 1.2:
            score += 15
        elif ratio >= 1.0:
            score += 10
        else:
            score += 5

    # MACD bullish crossover -- up to 20 pts
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig and macd > 0:
            score += 20
        elif macd > macd_sig:
            score += 15
        elif macd > 0:
            score += 10
        else:
            score += 5

    return min(score, 100.0)


def score_momentum(data: dict, spy_hist: pd.DataFrame) -> float:
    """Score momentum on a 0-100 scale."""
    score = 0.0
    hist = data["hist"]

    # 1-month and 3-month price change
    closes = hist["Close"]
    if len(closes) < 63:
        return 50.0  # neutral if not enough data

    month1_return = (closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]
    month3_return = (closes.iloc[-1] - closes.iloc[-63]) / closes.iloc[-63]

    # SPY comparison
    if spy_hist is not None and not spy_hist.empty and len(spy_hist) >= 63:
        spy_1m = (spy_hist["Close"].iloc[-1] - spy_hist["Close"].iloc[-21]) / spy_hist["Close"].iloc[-21]
        spy_3m = (spy_hist["Close"].iloc[-1] - spy_hist["Close"].iloc[-63]) / spy_hist["Close"].iloc[-63]
    else:
        spy_1m = 0.0
        spy_3m = 0.0

    # 1-month relative to SPY -- up to 50 pts
    rel_1m = month1_return - spy_1m
    if rel_1m >= 0.05:
        score += 50
    elif rel_1m >= 0.02:
        score += 40
    elif rel_1m >= 0:
        score += 30
    elif rel_1m >= -0.03:
        score += 20
    elif rel_1m >= -0.06:
        score += 10
    else:
        score += 5

    # 3-month relative to SPY -- up to 50 pts
    rel_3m = month3_return - spy_3m
    if rel_3m >= 0.05:
        score += 50
    elif rel_3m >= 0.02:
        score += 40
    elif rel_3m >= 0:
        score += 30
    elif rel_3m >= -0.03:
        score += 20
    elif rel_3m >= -0.06:
        score += 10
    else:
        score += 5

    return min(score, 100.0)


def get_verdict(score: float) -> str:
    """Return a plain-English verdict for a score."""
    if score >= 75:
        return "Strong buy candidate"
    elif score >= 55:
        return "Watch closely"
    elif score >= 35:
        return "Neutral"
    else:
        return "Avoid"


def generate_summary(data: dict, score: float) -> str:
    """Generate a 2-3 sentence summary for a top stock."""
    hist = data["hist"]
    pe = data.get("pe_ratio")
    rsi = hist["RSI"].iloc[-1]
    price = data["current_price"]
    ma50 = hist["MA50"].iloc[-1]
    macd = hist["MACD"].iloc[-1]
    macd_sig = hist["MACD_Signal"].iloc[-1]

    parts = []

    # RSI
    if pd.notna(rsi):
        if rsi < 30:
            parts.append(f"RSI of {rsi:.1f} suggests oversold conditions")
        elif rsi <= 55:
            parts.append(f"RSI of {rsi:.1f} indicates recovering momentum")
        else:
            parts.append(f"RSI of {rsi:.1f} shows moderate strength")

    # P/E
    if pe is not None and not np.isnan(pe):
        parts.append(f"P/E of {pe:.1f} is attractive")

    # MA
    if pd.notna(ma50):
        if price > ma50:
            parts.append("price is recovering above the 50-day MA")
        else:
            parts.append("price is below the 50-day MA, suggesting caution")

    # MACD
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig:
            parts.append("MACD shows a bullish crossover")
        else:
            parts.append("MACD has not yet confirmed a bullish crossover")

    summary = ". ".join(parts[:3]) + "."
    return summary


def get_ma_signal(data: dict) -> str:
    """Return a string describing the moving average signal."""
    hist = data["hist"]
    price = data["current_price"]
    ma50 = hist["MA50"].iloc[-1]
    ma200 = hist["MA200"].iloc[-1]
    if pd.isna(ma50) or pd.isna(ma200):
        return "N/A"
    if price > ma50 > ma200:
        return "Bullish (price > 50MA > 200MA)"
    elif price > ma50:
        return "Mixed (price > 50MA)"
    elif price > ma200:
        return "Weak (price > 200MA only)"
    else:
        return "Bearish (price < all MAs)"


def get_volume_signal(data: dict) -> str:
    """Return a string describing the volume signal."""
    ratio = data["latest_vol"] / data["avg_vol_30"] if data["avg_vol_30"] else 0
    if ratio >= 1.5:
        return f"High spike ({ratio:.1f}x avg)"
    elif ratio >= 1.2:
        return f"Above avg ({ratio:.1f}x)"
    else:
        return f"Normal ({ratio:.1f}x)"


# ---------------------------------------------------------------------------
# Crypto pipeline
# ---------------------------------------------------------------------------
def fetch_crypto_data(ticker: str):
    """Fetch crypto data (no P/E, debt/equity, or revenue fields). Returns None on failure."""
    try:
        t = _retry_yfinance(ticker)
        info = t.info or {}

        # Crypto price is the "Close" / current price in USD
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if current_price is None or current_price <= 0:
            return None

        avg_volume = info.get("averageVolume") or info.get("volume")

        # Crypto: fetch 1 year of data (need ~365 rows for 200-day MA calc, 24/7 trading)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 60:
            return None

        # Moving averages (50-day always, 200-day only if enough data)
        hist["MA50"] = hist["Close"].rolling(window=50).mean()
        hist["MA200"] = hist["Close"].rolling(window=200).mean()

        # RSI calculation
        delta = hist["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta.where(delta < 0, 0.0)).abs()
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        hist["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = hist["Close"].ewm(span=12, adjust=False).mean()
        ema26 = hist["Close"].ewm(span=26, adjust=False).mean()
        hist["MACD"] = ema12 - ema26
        hist["MACD_Signal"] = hist["MACD"].ewm(span=9, adjust=False).mean()

        # Volume
        avg_vol_30 = hist["Volume"].tail(30).mean()
        latest_vol = hist["Volume"].iloc[-1]

        return {
            "ticker": ticker,
            "info": info,
            "current_price": current_price,
            "pe_ratio": None,
            "debt_equity": None,
            "revenue_growth": None,
            "profit_margin": None,
            "avg_volume": avg_volume,
            "hist": hist,
            "avg_vol_30": avg_vol_30,
            "latest_vol": latest_vol,
        }
    except Exception as exc:
        logger.error(f"Failed to fetch crypto data for {ticker}: {exc}")
        return None


def passes_crypto_screen(data: dict) -> bool:
    """Light screening for crypto. Only checks price > $0.01 and non-empty history."""
    if data is None:
        return False
    if data["current_price"] < 0.01:
        return False
    return True


def score_crypto_technicals(data: dict) -> float:
    """Score crypto technical signals on a 0-100 scale (same structure as stocks)."""
    score = 0.0
    hist = data["hist"]
    rsi = hist["RSI"].iloc[-1]
    macd = hist["MACD"].iloc[-1]
    macd_sig = hist["MACD_Signal"].iloc[-1]
    price = data["current_price"]
    ma50 = hist["MA50"].iloc[-1]
    ma200 = hist["MA200"].iloc[-1]

    # RSI between 30 and 55 scores highest -- up to 30 pts
    if pd.notna(rsi):
        if 30 <= rsi <= 55:
            score += 30
        elif rsi < 30:
            score += 20
        elif rsi <= 70:
            score += 15
        else:
            score += 5

    # Price vs MAs -- up to 30 pts
    if pd.notna(ma50) and pd.notna(ma200):
        if price > ma50 > ma200:
            score += 30
        elif price > ma50 and price > ma200:
            score += 20
        elif price > ma200:
            score += 15
        elif price > ma50:
            score += 10
        else:
            score += 5
    elif pd.notna(ma50):
        if price > ma50:
            score += 15
        else:
            score += 5

    # Volume spike vs 30-day average -- up to 20 pts
    if data["avg_vol_30"] and data["avg_vol_30"] > 0:
        ratio = data["latest_vol"] / data["avg_vol_30"]
        if ratio >= 2.0:
            score += 20
        elif ratio >= 1.5:
            score += 15
        elif ratio >= 1.0:
            score += 10
        else:
            score += 5

    # MACD bullish crossover -- up to 20 pts
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig and macd > 0:
            score += 20
        elif macd > macd_sig:
            score += 15
        elif macd > 0:
            score += 10
        else:
            score += 5

    return min(score, 100.0)


def score_crypto_momentum(data: dict, btc_hist: pd.DataFrame = None) -> float:
    """Score crypto momentum on a 0-100 scale. Uses BTC as benchmark if provided."""
    score = 0.0
    hist = data["hist"]
    closes = hist["Close"]
    if len(closes) < 30:
        return 50.0

    # 1-month and 3-month (approx 30 & 90 days for crypto trades 24/7)
    month1_return = (closes.iloc[-1] - closes.iloc[-30]) / closes.iloc[-30]
    month3_idx = -min(90, len(closes) - 1)
    month3_return = (closes.iloc[-1] - closes.iloc[month3_idx]) / closes.iloc[month3_idx]

    # BTC comparison
    if btc_hist is not None and not btc_hist.empty and len(btc_hist) >= 30:
        btc_1m = (btc_hist["Close"].iloc[-1] - btc_hist["Close"].iloc[-30]) / btc_hist["Close"].iloc[-30]
        btc_3m_idx = -min(90, len(btc_hist) - 1)
        btc_3m = (btc_hist["Close"].iloc[-1] - btc_hist["Close"].iloc[btc_3m_idx]) / btc_hist["Close"].iloc[btc_3m_idx]
    else:
        btc_1m = 0.0
        btc_3m = 0.0

    # 1-month relative to BTC -- up to 50 pts
    rel_1m = month1_return - btc_1m
    if rel_1m >= 0.10:
        score += 50
    elif rel_1m >= 0.05:
        score += 40
    elif rel_1m >= 0:
        score += 30
    elif rel_1m >= -0.10:
        score += 20
    elif rel_1m >= -0.20:
        score += 10
    else:
        score += 5

    # 3-month relative to BTC -- up to 50 pts
    rel_3m = month3_return - btc_3m
    if rel_3m >= 0.10:
        score += 50
    elif rel_3m >= 0.05:
        score += 40
    elif rel_3m >= 0:
        score += 30
    elif rel_3m >= -0.10:
        score += 20
    elif rel_3m >= -0.20:
        score += 10
    else:
        score += 5

    return min(score, 100.0)


# ---------------------------------------------------------------------------
# Layman / Investment projection helpers
# ---------------------------------------------------------------------------
def generate_layman_summary(data: dict, total_score: float, ticker_type: str = "stock") -> str:
    """Return a plain-English summary explaining the metrics for non-experts."""
    hist = data["hist"]
    rsi = hist["RSI"].iloc[-1] if not hist["RSI"].empty else None
    macd = hist["MACD"].iloc[-1] if not hist["MACD"].empty else None
    macd_sig = hist["MACD_Signal"].iloc[-1] if not hist["MACD_Signal"].empty else None
    price = data["current_price"]
    ma50 = hist["MA50"].iloc[-1] if not hist["MA50"].empty else None
    ma200 = hist["MA200"].iloc[-1] if not hist["MA200"].empty else None

    parts = []

    if ticker_type == "crypto":
        parts.append(f"This cryptocurrency is trading at ${price:.4f}.")
    else:
        parts.append(f"This stock is trading at ${price:.2f}.")

    # RSI in simple terms
    if pd.notna(rsi):
        if rsi < 30:
            parts.append("The RSI (Relative Strength Index) is below 30 — this means it may be oversold and could bounce back.")
        elif rsi <= 55:
            parts.append("The RSI sits between 30-55, pointing to recovering momentum with room to grow.")
        elif rsi <= 70:
            parts.append("The RSI is showing moderate strength but is not yet overbought.")
        else:
            parts.append("The RSI is above 70, which can signal it's getting expensive or overbought.")

    # Moving averages in simple terms
    if pd.notna(ma50) and pd.notna(ma200):
        if price > ma50 > ma200:
            parts.append("Price is above both the 50-day and 200-day averages — a strong signal.")
        elif price > ma50:
            if ma50 < ma200:
                parts.append("Price is above the 50-day average but still below the 200-day (bearish long-term).")
            else:
                parts.append("Price is above the 50-day average, showing short-term improvement.")
        else:
            parts.append("Price is below both averages, showing weakness.")
    elif pd.notna(ma50):
        if price > ma50:
            parts.append("Price is above the 50-day average, showing short-term strength.")
        else:
            parts.append("Price is below the 50-day average, showing short-term weakness.")

    # MACD in simple terms
    if pd.notna(macd) and pd.notna(macd_sig):
        if macd > macd_sig:
            parts.append("The MACD (trend indicator) is showing a bullish crossover — momentum is shifting up.")
        else:
            parts.append("The MACD has not yet shown a bullish crossover — momentum may still be turning.")

    return " ".join(parts[:5])


def investment_projection(data: dict, total_score: float, timeframe_days: int = 90) -> dict:
    """Return a dict with hypothetical $1,000 investment projection. NOT financial advice!"""
    hist = data["hist"]
    closes = hist["Close"]

    # Use available history to estimate a forward return rate
    if len(closes) >= 90:
        past_return = (closes.iloc[-1] - closes.iloc[-90]) / closes.iloc[-90]
    elif len(closes) >= 30:
        past_return = (closes.iloc[-1] - closes.iloc[-30]) / closes.iloc[-30]
    else:
        past_return = 0.0

    # Scale by score and cap at reasonable bounds
    # Higher score = higher projected return, but never guarantee anything
    score_factor = total_score / 100.0
    base_return = past_return * score_factor
    base_return = max(-0.30, min(0.40, base_return))  # Cap return between -30% and +40%

    # For shorter timeframe, scale down
    if timeframe_days <= 30:
        projected_return = base_return * 0.6
    else:
        projected_return = base_return

    projected_value = 1000 * (1 + projected_return)

    return {
        "investment": 1000.0,
        "projected_value": round(projected_value, 2),
        "projected_return_pct": round(projected_return * 100, 1),
        "timeframe_days": timeframe_days,
    }
