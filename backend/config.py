"""
config.py
Loads environment variables and stores project settings.
"""

import os
from dotenv import load_dotenv

# Load .env variables into the environment
load_dotenv()

# ---------------------------------------------------------------------------
# Environment / Secrets
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Screening Thresholds
# ---------------------------------------------------------------------------
class Screening:
    MAX_PE = 35.0
    MAX_DEBT_TO_EQUITY = 2.0
    MIN_AVG_DAILY_VOLUME = 500_000
    MIN_PRICE = 5.0

# ---------------------------------------------------------------------------
# Scoring Weights (must sum to 100)
# ---------------------------------------------------------------------------
class Weights:
    FUNDAMENTALS = 0.40
    TECHNICALS = 0.40
    MOMENTUM = 0.20
