import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import numpy as np
import pandas as pd


def hist_stub(rsi=np.nan, macd=np.nan, macd_sig=np.nan, ma50=np.nan, ma200=np.nan):
    """Single-row hist DataFrame exposing only the last-row indicator values
    that the per-ticker scorers read via .iloc[-1]."""
    return pd.DataFrame({
        "RSI": [rsi],
        "MACD": [macd],
        "MACD_Signal": [macd_sig],
        "MA50": [ma50],
        "MA200": [ma200],
    })


def close_series(prices):
    """Hist DataFrame with only a Close column, for return-based (momentum /
    investment projection) calculations that index relative to length."""
    return pd.DataFrame({"Close": list(prices)})
