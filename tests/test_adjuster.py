"""Tests for the Adjuster engine."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from vn_corporate_actions import Adjuster

# ----------------------------------------------------------------------
# Single-action math
# ----------------------------------------------------------------------


def test_single_split(vnm_split_prices: pd.DataFrame) -> None:
    """Pre-split 200,000 should become 100,000 after a 1:2 split adjustment."""
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)

    out = adj.adjust_prices(vnm_split_prices, volume_col="volume")
    pre = out.loc[out["trade_date"] == date(2023, 8, 14)]
    post = out.loc[out["trade_date"] == date(2023, 8, 15)]

    assert pre["close"].iloc[0] == pytest.approx(100_000.0)
    assert post["close"].iloc[0] == pytest.approx(100_000.0)
    # Volume scales up by ratio on the pre-split date.
    assert pre["volume"].iloc[0] == pytest.approx(2_000.0)
    assert post["volume"].iloc[0] == pytest.approx(2_000.0)


def test_cash_dividend(vnm_dividend_prices: pd.DataFrame) -> None:
    """Cash dividend 5000 on prior close 70000 -> factor 65000/70000."""
    adj = Adjuster()
    adj.add_cash_dividend("VNM", "2024-06-12", amount=5_000)

    out = adj.adjust_prices(vnm_dividend_prices)
    pre = out.loc[out["trade_date"] == date(2024, 6, 11), "close"].iloc[0]
    post = out.loc[out["trade_date"] == date(2024, 6, 12), "close"].iloc[0]

    expected = 70_000.0 * (65_000.0 / 70_000.0)
    assert pre == pytest.approx(expected)
    assert post == pytest.approx(65_000.0)


def test_stock_dividend_10pct() -> None:
    """10% stock dividend scales pre-ex prices by 1/1.1."""
    df = pd.DataFrame(
        {
            "ticker": ["HPG", "HPG"],
            "trade_date": [date(2023, 5, 9), date(2023, 5, 10)],
            "close": [33_000.0, 30_000.0],
            "volume": [1_000.0, 1_100.0],
        }
    )
    adj = Adjuster()
    adj.add_stock_dividend("HPG", "2023-05-10", ratio=0.10)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2023, 5, 9), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2023, 5, 9), "volume"].iloc[0]

    assert pre_price == pytest.approx(33_000.0 / 1.10)
    assert pre_vol == pytest.approx(1_000.0 * 1.10)


def test_bonus_issue_20pct() -> None:
    """20% bonus issue scales pre-ex prices by 1/1.2."""
    df = pd.DataFrame(
        {
            "ticker": ["HPG", "HPG"],
            "trade_date": [date(2023, 7, 19), date(2023, 7, 20)],
            "close": [36_000.0, 30_000.0],
            "volume": [1_000.0, 1_200.0],
        }
    )
    adj = Adjuster()
    adj.add_bonus_issue("HPG", "2023-07-20", ratio=0.20)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2023, 7, 19), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2023, 7, 19), "volume"].iloc[0]

    assert pre_price == pytest.approx(36_000.0 / 1.20)
    assert pre_vol == pytest.approx(1_000.0 * 1.20)


def test_rights_issue() -> None:
    """1:5 rights at sub-price 10,000 on prior close 30,000.

    Theoretical ex-rights = (30000 + 0.2 * 10000) / 1.2 = 26666.67
    Factor = 26666.67 / 30000
    """
    df = pd.DataFrame(
        {
            "ticker": ["VIC", "VIC"],
            "trade_date": [date(2023, 8, 31), date(2023, 9, 1)],
            "close": [30_000.0, 26_666.67],
            "volume": [1_000.0, 1_200.0],
        }
    )
    adj = Adjuster()
    adj.add_rights_issue("VIC", "2023-09-01", ratio=0.20, subscription_price=10_000)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2023, 8, 31), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2023, 8, 31), "volume"].iloc[0]

    theoretical = (30_000.0 + 0.2 * 10_000.0) / 1.2
    expected = 30_000.0 * (theoretical / 30_000.0)
    assert pre_price == pytest.approx(expected, rel=1e-6)
    assert pre_price == pytest.approx(theoretical, rel=1e-6)
    assert pre_vol == pytest.approx(1_000.0 * 1.2)


def test_reverse_split() -> None:
    """2:1 reverse split — pre-ex prices multiplied by ratio."""
    df = pd.DataFrame(
        {
            "ticker": ["ABC", "ABC"],
            "trade_date": [date(2024, 1, 31), date(2024, 2, 1)],
            "close": [10_000.0, 20_000.0],
            "volume": [2_000.0, 1_000.0],
        }
    )
    adj = Adjuster()
    adj.add_reverse_split("ABC", "2024-02-01", ratio=2.0)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2024, 1, 31), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2024, 1, 31), "volume"].iloc[0]

    assert pre_price == pytest.approx(20_000.0)
    assert pre_vol == pytest.approx(1_000.0)


# ----------------------------------------------------------------------
# Composition and bookkeeping
# ----------------------------------------------------------------------


def test_multi_action_stacking() -> None:
    """A split on D1 and a cash dividend on D2 (D1 < D2) compound correctly."""
    # Dates: D1 = 2023-08-15 (split 2:1); D2 = 2024-06-12 (cash 5000)
    df = pd.DataFrame(
        {
            "ticker": ["VNM"] * 4,
            "trade_date": [
                date(2023, 8, 14),
                date(2023, 8, 15),
                date(2024, 6, 11),
                date(2024, 6, 12),
            ],
            "close": [200_000.0, 100_000.0, 70_000.0, 65_000.0],
        }
    )
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    adj.add_cash_dividend("VNM", "2024-06-12", amount=5_000)

    out = adj.adjust_prices(df)
    closes = out.set_index("trade_date")["close"]

    # Day before the split: factor = (1/2) * (65/70)
    assert closes[date(2023, 8, 14)] == pytest.approx(200_000.0 * 0.5 * (65_000.0 / 70_000.0))
    # Between split and dividend: only dividend factor applies.
    assert closes[date(2023, 8, 15)] == pytest.approx(100_000.0 * (65_000.0 / 70_000.0))
    assert closes[date(2024, 6, 11)] == pytest.approx(70_000.0 * (65_000.0 / 70_000.0))
    # Ex-dividend day and later: unchanged.
    assert closes[date(2024, 6, 12)] == pytest.approx(65_000.0)


def test_actions_for_sorted() -> None:
    adj = Adjuster()
    adj.add_cash_dividend("VNM", "2024-06-12", amount=5_000)
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    seq = adj.actions_for("VNM")
    assert [a.ex_date for a in seq] == [date(2023, 8, 15), date(2024, 6, 12)]


def test_unknown_ticker_returns_unchanged(multi_ticker_prices: pd.DataFrame) -> None:
    """Tickers without registered actions pass through untouched."""
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)

    out = adj.adjust_prices(multi_ticker_prices, volume_col="volume")
    hpg_in = multi_ticker_prices[multi_ticker_prices["ticker"] == "HPG"].reset_index(drop=True)
    hpg_out = out[out["ticker"] == "HPG"].reset_index(drop=True)
    pd.testing.assert_frame_equal(hpg_in, hpg_out)


def test_adjust_prices_multi_ticker(multi_ticker_prices: pd.DataFrame) -> None:
    """End-to-end DataFrame call with two tickers and two distinct actions."""
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    adj.add_stock_dividend("HPG", "2023-08-15", ratio=0.10)

    out = adj.adjust_prices(multi_ticker_prices, volume_col="volume")

    # First VNM row (before ex-date) should be halved.
    vnm = out[out["ticker"] == "VNM"].sort_values("trade_date").reset_index(drop=True)
    assert vnm.loc[0, "close"] == pytest.approx(200_000.0 * 0.5)
    # First HPG row (before ex-date) should be divided by 1.1.
    hpg = out[out["ticker"] == "HPG"].sort_values("trade_date").reset_index(drop=True)
    assert hpg.loc[0, "close"] == pytest.approx(30_000.0 / 1.10)


def test_adjustment_factor_before_and_after() -> None:
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)

    # Before ex-date: full backward factor applies.
    assert adj.adjustment_factor("VNM", "2023-08-14") == pytest.approx(0.5)
    # On / after ex-date: factor is 1.0.
    assert adj.adjustment_factor("VNM", "2023-08-15") == pytest.approx(1.0)
    assert adj.adjustment_factor("VNM", "2024-01-01") == pytest.approx(1.0)


def test_adjust_series_basic() -> None:
    """Lower-level array entry point matches the DataFrame path."""
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)

    out = adj.adjust_series(
        "VNM",
        [date(2023, 8, 14), date(2023, 8, 15)],
        [200_000.0, 100_000.0],
    )
    assert out.tolist() == pytest.approx([100_000.0, 100_000.0])


def test_repr_and_len() -> None:
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    adj.add_cash_dividend("VNM", "2024-06-12", amount=5_000)
    assert len(adj) == 2
    assert "Adjuster" in repr(adj)


def test_missing_columns_raises() -> None:
    adj = Adjuster()
    df = pd.DataFrame({"ticker": ["VNM"], "trade_date": [date(2023, 1, 1)]})
    with pytest.raises(KeyError):
        adj.adjust_prices(df)


# ----------------------------------------------------------------------
# Additional action types
# ----------------------------------------------------------------------


def test_special_cash_dividend() -> None:
    """Special cash dividend behaves like a regular cash dividend."""
    df = pd.DataFrame(
        {
            "ticker": ["VNM", "VNM"],
            "trade_date": [date(2024, 6, 11), date(2024, 6, 12)],
            "close": [70_000.0, 62_000.0],
        }
    )
    adj = Adjuster()
    adj.add_special_cash_dividend("VNM", "2024-06-12", amount=8_000)

    out = adj.adjust_prices(df)
    pre = out.loc[out["trade_date"] == date(2024, 6, 11), "close"].iloc[0]
    assert pre == pytest.approx(70_000.0 * (62_000.0 / 70_000.0))


def test_return_of_capital() -> None:
    """Return of capital lowers pre-ex prices like a cash dividend."""
    df = pd.DataFrame(
        {
            "ticker": ["VNM", "VNM"],
            "trade_date": [date(2024, 6, 11), date(2024, 6, 12)],
            "close": [70_000.0, 67_000.0],
        }
    )
    adj = Adjuster()
    adj.add_return_of_capital("VNM", "2024-06-12", amount=3_000)

    out = adj.adjust_prices(df)
    pre = out.loc[out["trade_date"] == date(2024, 6, 11), "close"].iloc[0]
    assert pre == pytest.approx(70_000.0 * (67_000.0 / 70_000.0))


def test_spinoff() -> None:
    """Spin-off drops parent price by distributed value per share."""
    df = pd.DataFrame(
        {
            "ticker": ["VIC", "VIC"],
            "trade_date": [date(2024, 3, 31), date(2024, 4, 1)],
            "close": [50_000.0, 38_000.0],
        }
    )
    adj = Adjuster()
    adj.add_spinoff("VIC", "2024-04-01", value_per_share=12_000)

    out = adj.adjust_prices(df)
    pre = out.loc[out["trade_date"] == date(2024, 3, 31), "close"].iloc[0]
    assert pre == pytest.approx(50_000.0 * ((50_000.0 - 12_000.0) / 50_000.0))


def test_par_value_change() -> None:
    """Halving par doubles shares: pre-ex price halved, volume doubled."""
    df = pd.DataFrame(
        {
            "ticker": ["VNM", "VNM"],
            "trade_date": [date(2024, 2, 29), date(2024, 3, 1)],
            "close": [100_000.0, 50_000.0],
            "volume": [1_000.0, 2_000.0],
        }
    )
    adj = Adjuster()
    adj.add_par_value_change("VNM", "2024-03-01", old_par=10_000, new_par=5_000)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2024, 2, 29), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2024, 2, 29), "volume"].iloc[0]
    assert pre_price == pytest.approx(50_000.0)
    assert pre_vol == pytest.approx(2_000.0)


def test_esop_issuance() -> None:
    """ESOP issuance dilutes like a rights issue (TERP)."""
    df = pd.DataFrame(
        {
            "ticker": ["FPT", "FPT"],
            "trade_date": [date(2024, 1, 31), date(2024, 2, 1)],
            "close": [100_000.0, 95_714.29],
            "volume": [1_000.0, 1_050.0],
        }
    )
    adj = Adjuster()
    adj.add_esop_issuance("FPT", "2024-02-01", ratio=0.05, issue_price=10_000)

    out = adj.adjust_prices(df, volume_col="volume")
    pre_price = out.loc[out["trade_date"] == date(2024, 1, 31), "close"].iloc[0]
    pre_vol = out.loc[out["trade_date"] == date(2024, 1, 31), "volume"].iloc[0]
    theoretical = (100_000.0 + 0.05 * 10_000.0) / 1.05
    assert pre_price == pytest.approx(theoretical, rel=1e-6)
    assert pre_vol == pytest.approx(1_000.0 * 1.05)


def test_esop_free_grant() -> None:
    """A free ESOP grant (issue_price=0) is equivalent to a stock dividend."""
    df = pd.DataFrame(
        {
            "ticker": ["FPT", "FPT"],
            "trade_date": [date(2024, 1, 31), date(2024, 2, 1)],
            "close": [105_000.0, 100_000.0],
        }
    )
    adj = Adjuster()
    adj.add_esop_issuance("FPT", "2024-02-01", ratio=0.05, issue_price=0)

    out = adj.adjust_prices(df)
    pre = out.loc[out["trade_date"] == date(2024, 1, 31), "close"].iloc[0]
    assert pre == pytest.approx(105_000.0 / 1.05)


def test_ticker_change_is_price_neutral() -> None:
    """Ticker change leaves prices and volumes untouched."""
    df = pd.DataFrame(
        {
            "ticker": ["MSN", "MSN"],
            "trade_date": [date(2022, 12, 31), date(2023, 1, 1)],
            "close": [80_000.0, 81_000.0],
            "volume": [1_000.0, 1_100.0],
        }
    )
    adj = Adjuster()
    adj.add_ticker_change("MSN", "2023-01-01", new_ticker="MSN2")

    out = adj.adjust_prices(df, volume_col="volume")
    pd.testing.assert_frame_equal(out, df)


def test_cash_then_spinoff_stacking() -> None:
    """Cash dividend and spin-off on different dates compound correctly."""
    df = pd.DataFrame(
        {
            "ticker": ["VIC"] * 3,
            "trade_date": [date(2024, 3, 31), date(2024, 4, 1), date(2024, 6, 12)],
            "close": [50_000.0, 38_000.0, 40_000.0],
        }
    )
    adj = Adjuster()
    adj.add_spinoff("VIC", "2024-04-01", value_per_share=12_000)
    adj.add_cash_dividend("VIC", "2024-06-12", amount=2_000)

    out = adj.adjust_prices(df)
    closes = out.set_index("trade_date")["close"]
    spin_factor = (50_000.0 - 12_000.0) / 50_000.0
    # prior close before the cash dividend is 38,000.
    cash_factor = (38_000.0 - 2_000.0) / 38_000.0
    assert closes[date(2024, 3, 31)] == pytest.approx(50_000.0 * spin_factor * cash_factor)
    assert closes[date(2024, 4, 1)] == pytest.approx(38_000.0 * cash_factor)
    assert closes[date(2024, 6, 12)] == pytest.approx(40_000.0)


def test_len_and_iter_cover_all_tickers() -> None:
    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    adj.add_bonus_issue("HPG", "2023-07-20", ratio=0.20)
    assert len(adj) == 2
    assert sorted(a.ticker for a in adj) == ["HPG", "VNM"]
    assert adj.tickers() == ["HPG", "VNM"]
