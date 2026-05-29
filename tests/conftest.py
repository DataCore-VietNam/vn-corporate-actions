"""Shared pytest fixtures for vn-corporate-actions."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest


def _business_days(start: date, n: int) -> list[date]:
    """Generate ``n`` Mon-Fri trading days starting at ``start``."""
    days: list[date] = []
    cur = start
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


@pytest.fixture
def vnm_split_prices() -> pd.DataFrame:
    """Two trading days bracketing a 2:1 split on 2023-08-15."""
    return pd.DataFrame(
        {
            "ticker": ["VNM", "VNM"],
            "trade_date": [date(2023, 8, 14), date(2023, 8, 15)],
            "close": [200_000.0, 100_000.0],
            "volume": [1_000.0, 2_000.0],
        }
    )


@pytest.fixture
def vnm_dividend_prices() -> pd.DataFrame:
    """Two trading days bracketing a cash dividend on 2024-06-12."""
    return pd.DataFrame(
        {
            "ticker": ["VNM", "VNM"],
            "trade_date": [date(2024, 6, 11), date(2024, 6, 12)],
            "close": [70_000.0, 65_000.0],
            "volume": [1_000.0, 1_500.0],
        }
    )


@pytest.fixture
def multi_ticker_prices() -> pd.DataFrame:
    """Two tickers, ten days each — useful for end-to-end DataFrame tests."""
    days = _business_days(date(2023, 8, 7), 10)
    rows = []
    for ticker, base in [("VNM", 200_000.0), ("HPG", 30_000.0)]:
        for i, d in enumerate(days):
            rows.append(
                {
                    "ticker": ticker,
                    "trade_date": d,
                    "close": base + i * 100,
                    "volume": 1_000 + i * 10,
                }
            )
    return pd.DataFrame(rows)
