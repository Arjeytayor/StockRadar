"""
telegram_alert.py
Formats and sends Telegram messages with the top stock and crypto picks.
"""

import logging
import requests
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def format_telegram_message(results: list, top_n: int = 5) -> str:
    """
    Format the screener results into a Telegram-friendly message.
    Separates stocks and crypto, includes layman summaries and projections.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Determine market mood based on SPY 5-day trend
    try:
        import yfinance as yf
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="5d")
        if len(spy_hist) >= 2:
            trend = spy_hist["Close"].iloc[-1] - spy_hist["Close"].iloc[0]
            if trend > 0.01:
                mood = "Bullish"
            elif trend < -0.01:
                mood = "Bearish"
            else:
                mood = "Neutral"
        else:
            mood = "Neutral"
    except Exception:
        mood = "Neutral"

    # Split results by type
    stocks = [r for r in results[:top_n] if r.get("type") == "stock"]
    crypto = [r for r in results[:top_n] if r.get("type") == "crypto"]
    top_stocks = stocks[:top_n]
    top_crypto = crypto[:top_n]

    lines = [
        f"📊 Daily Screening — {today}",
        f"Market mood: {mood} (based on SPY 5-day trend)",
        "",
        "⚠️ ⚠️ ⚠️   NOT FINANCIAL ADVICE   ⚠️ ⚠️ ⚠️",
        "⚠️ Always do your own research before investing any money. ⚠️",
        "⚠️ Past performance does not guarantee future results. ⚠️",
        "",
    ]

    if top_stocks:
        lines.append("🏆 TOP STOCKS 🏆")
        lines.append("")
        for i, r in enumerate(top_stocks, start=1):
            inv30 = r.get("investment_30d", {})
            inv90 = r.get("investment_90d", {})

            stock_info = (
                f"{i}. {r['ticker']} — Score: {r['total_score']:.0f}/100  "
                f"| Price: ${r['current_price']:.2f}  | P/E: {r['pe']:.1f}  | RSI: {r['rsi']:.1f}\n"
                f"    📖 In Plain English: {r.get('layman_summary', 'N/A')[:200]}\n"
                f"    📰 Why it's interesting: {r.get('summary', 'N/A')[:150]}...\n"
                f"    💰 If you invested $1,000 today, you'd get approximately: "
                f"${inv30.get('projected_value', 'N/A')} in 30 days, "
                f"${inv90.get('projected_value', 'N/A')} in 90 days."
            )
            lines.append(stock_info)
            lines.append("")

    if top_crypto:
        lines.append("")
        lines.append("🪙 TOP CRYPTO 🪙")
        lines.append("")
        for i, r in enumerate(top_crypto, start=1):
            inv30 = r.get("investment_30d", {})
            inv90 = r.get("investment_90d", {})

            crypto_info = (
                f"{i}. {r['ticker']} — Score: {r['total_score']:.0f}/100  "
                f"| Price: ${r['current_price']:.2f}  | RSI: {r['rsi']:.1f}\n"
                f"    📖 In Plain English: {r.get('layman_summary', 'N/A')[:200]}\n"
                f"    📰 Why it's interesting: {r.get('summary', 'N/A')[:150]}...\n"
                f"    💰 If you'd invested $1,000 today, you'd get approximately: "
                f"${inv30.get('projected_value', 'N/A')} in 30 days, "
                f"${inv90.get('projected_value', 'N/A')} in 90 days."
            )
            lines.append(crypto_info)
            lines.append("")

    lines.extend([
        "⚠️ ⚠️ ⚠️   NOT FINANCIAL ADVICE   ⚠️ ⚠️ ⚠️",
        "This is a screening tool. It uses historical data and common indicators.",
        "Crypto is volatile. Stocks carry risk. Never invest money you can't afford to lose.",
    ])

    message = "\n".join(lines)
    return message


def send_telegram_alert(message: str) -> bool:
    """
    Send a message via Telegram bot. Return True on success.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing. Message not sent.")
        return False

    url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }

    try:
        response = requests.post(url, data=payload, timeout=30)
        if response.status_code == 200:
            logger.info("Telegram alert sent successfully.")
            return True
        else:
            logger.error(f"Telegram send failed: {response.status_code} {response.text}")
            return False
    except Exception as exc:
        logger.error(f"Telegram send exception: {exc}")
        return False
