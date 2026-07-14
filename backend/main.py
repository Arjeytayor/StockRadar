"""FastAPI server that exposes the StockRadar screener."""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from scoring import (
    DEFAULT_WATCHLIST,
    CRYPTO_WATCHLIST,
    fetch_stock_data,
    fetch_crypto_data,
    passes_screen,
    passes_crypto_screen,
    score_fundamentals,
    score_technicals,
    score_momentum,
    score_crypto_technicals,
    score_crypto_momentum,
    get_verdict,
    generate_layman_summary,
    investment_projection,
    generate_summary,
    SECTOR_MAP,
    get_ma_signal,
    get_volume_signal,
)
from config import Weights
import yfinance as yf
import pandas as pd

app = FastAPI(title="StockRadar API", version="2.0")

# Allow the frontend (localhost:5173 by default) to call us.
# Set CORS_ORIGINS to a comma-separated list of domains in production.
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScreenRequest(BaseModel):
    watchlist: str = "default"  # default, sp500, crypto
    top: int = 5
    include_crypto: bool = True
    sector: Optional[str] = None


class ScreenResult(BaseModel):
    ticker: str
    company: str
    sector: str
    type: str
    current_price: float
    total_score: float
    pe: float
    rsi: float
    ma_signal: str
    volume_signal: str
    verdict: str
    summary: str
    layman_summary: str
    investment_30d: dict
    investment_90d: dict


# ---------------------------------------------------------------------------
# Re-use the exact logic from your screener.py
# ---------------------------------------------------------------------------
def _run_screening(watchlist_type: str = "default",
                   top_n: int = 5,
                   include_crypto: bool = True,
                   sector_filter: Optional[str] = None):
    """Run the same pipeline as screener.py, return list of dicts."""

    # Resolve watchlist
    if watchlist_type == "sp500":
        from scoring import fetch_sp500_tickers
        tickers = fetch_sp500_tickers()
    elif watchlist_type == "crypto":
        tickers = []
        include_crypto = True
    else:
        tickers = DEFAULT_WATCHLIST
        include_crypto = not (watchlist_type == "crypto" or not include_crypto)

    # --- Stocks --------------------------------------------------------------
    spy_hist = None
    try:
        spy_hist = yf.Ticker("SPY").history(period="6mo")
    except Exception:
        pass

    all_data = []
    for t in tickers:
        data = fetch_stock_data(t)
        if data:
            all_data.append(data)

    # Sector-average P/E
    pe_by_sector = {}
    for s, sector in SECTOR_MAP.items():
        if sector not in pe_by_sector:
            pe_by_sector[sector] = []
    for data in all_data:
        t = data["ticker"]
        sector = SECTOR_MAP.get(t)
        pe = data.get("pe_ratio")
        if sector and pe and not pd.isna(pe):
            pe_by_sector[sector].append(pe)
    sector_avg_pe = {s: sum(v)/len(v) if v else None for s, v in pe_by_sector.items()}

    scored = []
    for data in all_data:
        if not passes_screen(data):
            continue
        ticker = data["ticker"]
        sector = SECTOR_MAP.get(ticker, "Unknown")
        if sector_filter and sector != sector_filter.lower().replace(" ", "_"):
            continue
        f_score = score_fundamentals(data, sector_avg_pe)
        t_score = score_technicals(data)
        m_score = score_momentum(data, spy_hist)
        total = f_score * Weights.FUNDAMENTALS + t_score * Weights.TECHNICALS + m_score * Weights.MOMENTUM
        scored.append({
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
            "summary": generate_summary(data, total),
            "layman_summary": generate_layman_summary(data, total, "stock"),
            "investment_30d": investment_projection(data, total, 30),
            "investment_90d": investment_projection(data, total, 90)
        })

    # --- Crypto --------------------------------------------------------------
    if include_crypto and watchlist_type != "crypto":
        btc_hist = None
        try:
            btc_hist = yf.Ticker("BTC-USD").history(period="6mo")
        except Exception:
            pass
        for t in CRYPTO_WATCHLIST:
            data = fetch_crypto_data(t)
            if not data or not passes_crypto_screen(data):
                continue
            t_score = score_crypto_technicals(data)
            m_score = score_crypto_momentum(data, btc_hist)
            total = t_score * 0.60 + m_score * 0.40
            scored.append({
                "ticker": t.replace("-USD", ""),
                "company": data["info"].get("longName", t.replace("-USD", "")),
                "sector": "Crypto",
                "type": "crypto",
                "current_price": data["current_price"],
                "total_score": total,
                "pe": float("nan"),
                "rsi": data["hist"]["RSI"].iloc[-1],
                "ma_signal": get_ma_signal(data),
                "volume_signal": get_volume_signal(data),
                "verdict": get_verdict(total),
                "summary": f"Crypto score: {total:.1f}",
                "layman_summary": generate_layman_summary(data, total, "crypto"),
                "investment_30d": investment_projection(data, total, 30),
                "investment_90d": investment_projection(data, total, 90),
            })

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored[:top_n]


@app.post("/api/screen", response_model=List[ScreenResult])
def screen(request: ScreenRequest):
    try:
        results = _run_screening(
            watchlist_type=request.watchlist,
            top_n=request.top,
            include_crypto=request.include_crypto,
            sector_filter=request.sector,
        )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
