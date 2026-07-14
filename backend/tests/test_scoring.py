"""Tests for scoring.py -- pure scoring/screening logic (no network calls)."""
import pytest

from conftest import hist_stub, close_series

from config import Screening
from scoring import (
    passes_screen,
    score_fundamentals,
    score_technicals,
    score_momentum,
    passes_crypto_screen,
    score_crypto_technicals,
    score_crypto_momentum,
    get_verdict,
    get_ma_signal,
    get_volume_signal,
    investment_projection,
)


def make_screen_data(**overrides):
    data = {
        "current_price": 100.0,
        "pe_ratio": 15.0,
        "debt_equity": 0.5,
        "revenue_growth": 0.1,
        "avg_volume": 1_000_000,
    }
    data.update(overrides)
    return data


class TestPassesScreen:
    def test_none_data_fails(self):
        assert passes_screen(None) is False

    def test_good_fundamentals_pass(self):
        assert passes_screen(make_screen_data()) is True

    def test_negative_revenue_growth_fails(self):
        assert passes_screen(make_screen_data(revenue_growth=-0.01)) is False

    def test_missing_revenue_growth_fails(self):
        assert passes_screen(make_screen_data(revenue_growth=None)) is False

    def test_pe_above_max_fails(self):
        assert passes_screen(make_screen_data(pe_ratio=Screening.MAX_PE + 0.01)) is False

    def test_pe_at_max_boundary_passes(self):
        assert passes_screen(make_screen_data(pe_ratio=Screening.MAX_PE)) is True

    def test_missing_pe_fails(self):
        assert passes_screen(make_screen_data(pe_ratio=None)) is False

    def test_debt_equity_above_max_fails(self):
        assert passes_screen(make_screen_data(debt_equity=Screening.MAX_DEBT_TO_EQUITY + 0.01)) is False

    def test_volume_below_min_fails(self):
        assert passes_screen(make_screen_data(avg_volume=Screening.MIN_AVG_DAILY_VOLUME - 1)) is False

    def test_price_below_min_fails(self):
        assert passes_screen(make_screen_data(current_price=Screening.MIN_PRICE - 0.01)) is False


class TestScoreFundamentals:
    def test_low_pe_high_growth_scores_max(self):
        data = {"ticker": "AAPL", "pe_ratio": 10, "revenue_growth": 0.25, "profit_margin": 0.25, "debt_equity": 0.2}
        assert score_fundamentals(data, sector_avg_pe={"tech": 20}) == 100.0

    def test_high_relative_pe_and_missing_fields_scores_low(self):
        data = {"ticker": "AAPL", "pe_ratio": 30, "revenue_growth": None, "profit_margin": None, "debt_equity": None}
        assert score_fundamentals(data, sector_avg_pe={"tech": 10}) == 5.0

    def test_unknown_sector_falls_back_to_own_pe_as_average(self):
        data = {"ticker": "ZZZZ", "pe_ratio": 15, "revenue_growth": None, "profit_margin": None, "debt_equity": None}
        # ZZZZ isn't in SECTOR_MAP -> sector "unknown" -> avg_pe falls back to pe itself -> ratio 1.0
        assert score_fundamentals(data, sector_avg_pe={}) == 20.0

    def test_score_never_exceeds_100(self):
        data = {"ticker": "AAPL", "pe_ratio": 5, "revenue_growth": 0.9, "profit_margin": 0.9, "debt_equity": 0.05}
        assert score_fundamentals(data, sector_avg_pe={"tech": 100}) <= 100.0


class TestScoreTechnicals:
    def test_ideal_setup_scores_max(self):
        data = {
            "hist": hist_stub(rsi=45, macd=1.0, macd_sig=0.5, ma50=110, ma200=100),
            "current_price": 120,
            "avg_vol_30": 1_000_000,
            "latest_vol": 1_600_000,
        }
        # 30 (RSI 30-55) + 30 (price>ma50>ma200) + 20 (vol>=1.5x) + 20 (macd>sig & macd>0)
        assert score_technicals(data) == 100.0

    def test_weak_setup_scores_low(self):
        data = {
            "hist": hist_stub(rsi=80, macd=-1.0, macd_sig=-0.5, ma50=110, ma200=120),
            "current_price": 90,
            "avg_vol_30": 1_000_000,
            "latest_vol": 500_000,
        }
        # 5 (RSI>70) + 5 (price below both MAs) + 5 (vol<1.0x) + 5 (macd<sig & macd<0)
        assert score_technicals(data) == 20.0

    def test_all_nan_indicators_contribute_nothing(self):
        data = {
            "hist": hist_stub(),
            "current_price": 100,
            "avg_vol_30": 0,
            "latest_vol": 0,
        }
        assert score_technicals(data) == 0.0


class TestGetVerdict:
    @pytest.mark.parametrize("score,expected", [
        (75, "Strong buy candidate"),
        (74.99, "Watch closely"),
        (55, "Watch closely"),
        (54.99, "Neutral"),
        (35, "Neutral"),
        (34.99, "Avoid"),
        (0, "Avoid"),
    ])
    def test_boundaries(self, score, expected):
        assert get_verdict(score) == expected


class TestGetMaSignal:
    def test_bullish_when_price_above_both_mas_in_order(self):
        data = {"hist": hist_stub(ma50=110, ma200=100), "current_price": 120}
        assert get_ma_signal(data).startswith("Bullish")

    def test_bearish_when_price_below_both_mas(self):
        data = {"hist": hist_stub(ma50=110, ma200=100), "current_price": 90}
        assert get_ma_signal(data).startswith("Bearish")

    def test_na_when_mas_missing(self):
        data = {"hist": hist_stub(), "current_price": 100}
        assert get_ma_signal(data) == "N/A"


class TestGetVolumeSignal:
    def test_high_spike(self):
        assert "High spike" in get_volume_signal({"avg_vol_30": 1_000_000, "latest_vol": 2_000_000})

    def test_normal(self):
        assert "Normal" in get_volume_signal({"avg_vol_30": 1_000_000, "latest_vol": 900_000})

    def test_zero_avg_volume_treated_as_zero_ratio(self):
        assert "Normal" in get_volume_signal({"avg_vol_30": 0, "latest_vol": 500})


class TestScoreMomentum:
    def test_outperforming_spy_scores_max(self):
        closes = [100.0] * 62 + [130.0]
        data = {"hist": close_series(closes)}
        spy_hist = close_series([100.0] * 63)
        assert score_momentum(data, spy_hist) == 100.0

    def test_underperforming_spy_scores_min(self):
        closes = [100.0] * 62 + [70.0]
        data = {"hist": close_series(closes)}
        spy_hist = close_series([100.0] * 63)
        assert score_momentum(data, spy_hist) == 10.0

    def test_short_history_returns_neutral(self):
        data = {"hist": close_series([100.0] * 10)}
        assert score_momentum(data, None) == 50.0

    def test_missing_spy_hist_benchmarks_against_zero(self):
        closes = [100.0] * 62 + [105.0]
        data = {"hist": close_series(closes)}
        assert score_momentum(data, None) == 100.0


class TestInvestmentProjection:
    def test_returns_expected_shape(self):
        closes = [100.0] * 89 + [110.0]
        result = investment_projection({"hist": close_series(closes)}, total_score=100, timeframe_days=90)
        assert set(result.keys()) == {"investment", "projected_value", "projected_return_pct", "timeframe_days"}
        assert result["investment"] == 1000.0
        assert result["timeframe_days"] == 90

    def test_score_scales_projected_return(self):
        closes = [100.0] * 89 + [110.0]
        data = {"hist": close_series(closes)}
        full = investment_projection(data, total_score=100, timeframe_days=90)
        half = investment_projection(data, total_score=50, timeframe_days=90)
        assert half["projected_return_pct"] < full["projected_return_pct"]

    def test_return_is_capped_at_40_percent(self):
        closes = [100.0] * 89 + [1000.0]
        data = {"hist": close_series(closes)}
        result = investment_projection(data, total_score=100, timeframe_days=90)
        assert result["projected_return_pct"] == 40.0

    def test_short_timeframe_scaled_down(self):
        closes = [100.0] * 89 + [110.0]
        data = {"hist": close_series(closes)}
        r30 = investment_projection(data, total_score=100, timeframe_days=30)
        r90 = investment_projection(data, total_score=100, timeframe_days=90)
        assert abs(r30["projected_return_pct"]) < abs(r90["projected_return_pct"])

    def test_short_history_uses_zero_return(self):
        result = investment_projection({"hist": close_series([100.0] * 5)}, total_score=100, timeframe_days=90)
        assert result["projected_return_pct"] == 0.0


class TestPassesCryptoScreen:
    def test_none_fails(self):
        assert passes_crypto_screen(None) is False

    def test_below_min_price_fails(self):
        assert passes_crypto_screen({"current_price": 0.005}) is False

    def test_valid_price_passes(self):
        assert passes_crypto_screen({"current_price": 1.23}) is True


class TestScoreCryptoTechnicals:
    def test_ideal_setup_scores_max(self):
        data = {
            "hist": hist_stub(rsi=45, macd=1.0, macd_sig=0.5, ma50=110, ma200=100),
            "current_price": 120,
            "avg_vol_30": 1_000_000,
            "latest_vol": 2_100_000,
        }
        # 30 (RSI) + 30 (MA order) + 20 (vol>=2.0x) + 20 (bullish macd)
        assert score_crypto_technicals(data) == 100.0


class TestScoreCryptoMomentum:
    def test_short_history_returns_neutral(self):
        assert score_crypto_momentum({"hist": close_series([100.0] * 5)}, None) == 50.0

    def test_3month_lookback_uses_negative_index_not_absolute_position(self):
        # Regression test: month3 return must be measured from ~90 days before
        # the most recent close, not from a fixed offset off the start of the
        # fetched window. With 200 flat days at 100 followed by a spike to 115,
        # both the 1-month and (clamped) 3-month lookback land in the flat
        # region, so the two returns must be equal.
        closes = [100.0] * 199 + [115.0]
        data = {"hist": close_series(closes)}
        score = score_crypto_momentum(data, btc_hist=None)
        month1_return = (115.0 - 100.0) / 100.0
        assert month1_return >= 0.10  # both legs should hit the top +50 bucket
        assert score == 100.0
