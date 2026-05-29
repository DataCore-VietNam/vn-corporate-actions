"""Runnable example: backwards-adjust a small VNM price series.

Run with:

    python examples/basic_usage.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from vn_corporate_actions import Adjuster


def main() -> None:
    prices = pd.DataFrame(
        {
            "ticker": ["VNM"] * 4,
            "trade_date": [
                date(2023, 8, 14),  # day before 2:1 split
                date(2023, 8, 15),  # split ex-date
                date(2024, 6, 11),  # day before cash dividend
                date(2024, 6, 12),  # cash dividend ex-date
            ],
            "close": [200_000.0, 100_000.0, 70_000.0, 65_000.0],
            "volume": [1_000.0, 2_000.0, 1_000.0, 1_500.0],
        }
    )

    adj = Adjuster()
    adj.add_split("VNM", "2023-08-15", ratio=2.0)
    adj.add_cash_dividend("VNM", "2024-06-12", amount=5_000)

    adjusted = adj.adjust_prices(prices, volume_col="volume")

    print("Original:")
    print(prices.to_string(index=False))
    print()
    print("Adjusted:")
    print(adjusted.to_string(index=False))


if __name__ == "__main__":
    main()
