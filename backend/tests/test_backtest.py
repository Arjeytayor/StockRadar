"""Tests for backtest.py."""
import pandas as pd
import pytest

import backtest


class FakeTicker:
    def __init__(self, hist_df):
        self._hist_df = hist_df

    def history(self, period=None):
        return self._hist_df


def _hist(closes):
    return pd.DataFrame({"Close": closes})


class TestCompareToMarket:
    def test_beats_market(self):
        assert backtest.compare_to_market(0.10, 0.02) == "Beat market"

    def test_underperforms_market(self):
        assert backtest.compare_to_market(0.01, 0.05) == "Underperformed market"

    def test_matches_market_within_1pct_band(self):
        assert backtest.compare_to_market(0.05, 0.045) == "Matched market"

    def test_boundary_exactly_at_1pct_counts_as_matched(self):
        # diff of exactly +/-0.01 does not satisfy the strict > / < comparisons
        assert backtest.compare_to_market(0.06, 0.05) == "Matched market"
        assert backtest.compare_to_market(0.05, 0.06) == "Matched market"


class TestFetchThreeMonthReturn:
    def test_computes_percentage_return(self, monkeypatch):
        monkeypatch.setattr(backtest.yf, "Ticker", lambda t: FakeTicker(_hist([100.0, 110.0])))
        assert backtest.fetch_three_month_return("AAPL") == pytest.approx(0.10)

    def test_empty_history_returns_zero(self, monkeypatch):
        monkeypatch.setattr(backtest.yf, "Ticker", lambda t: FakeTicker(_hist([])))
        assert backtest.fetch_three_month_return("AAPL") == 0.0

    def test_single_row_history_returns_zero(self, monkeypatch):
        monkeypatch.setattr(backtest.yf, "Ticker", lambda t: FakeTicker(_hist([100.0])))
        assert backtest.fetch_three_month_return("AAPL") == 0.0

    def test_zero_start_price_returns_zero(self, monkeypatch):
        monkeypatch.setattr(backtest.yf, "Ticker", lambda t: FakeTicker(_hist([0.0, 50.0])))
        assert backtest.fetch_three_month_return("AAPL") == 0.0

    def test_exception_is_caught_and_returns_zero(self, monkeypatch):
        def boom(t):
            raise RuntimeError("network down")
        monkeypatch.setattr(backtest.yf, "Ticker", boom)
        assert backtest.fetch_three_month_return("AAPL") == 0.0


class TestRunBacktest:
    def test_combines_ticker_and_spy_returns(self, monkeypatch):
        def fake_return(ticker):
            return {"AAPL": 0.10, "SPY": 0.03}[ticker]

        monkeypatch.setattr(backtest, "fetch_three_month_return", fake_return)

        result = backtest.run_backtest("AAPL")

        assert result == {
            "ticker": "AAPL",
            "stock_return": 10.0,
            "spy_return": 3.0,
            "difference": 7.0,
            "label": "Beat market",
        }
