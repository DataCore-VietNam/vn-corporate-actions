# vn-corporate-actions

Library for handling Vietnamese equity corporate actions: stock splits, dividends (cash + stock), bonus issues, rights offerings. Provides adjustment factors for clean historical price series.

```python
from vn_corporate_actions import Adjuster

adj = Adjuster()
adj.add_split(ticker="VNM", ex_date="2023-08-15", ratio=2.0)
adj.add_cash_dividend(ticker="VNM", ex_date="2024-06-12", amount=2900)

# Apply backwards adjustment to a price series
adjusted = adj.adjust_prices(df, ticker_col="ticker", date_col="trade_date", price_col="close")
```

## Why this exists

Adjusted close in Vietnamese data feeds is often wrong or inconsistent across vendors. This library lets you:

- Maintain your own corporate-actions ledger
- Recompute adjusted series deterministically
- Handle Vietnam-specific cases: bonus shares, stock dividends (very common), rights issues with subscription discounts

## Action types supported

| Type | Description |
|------|-------------|
| `split` | Forward stock split |
| `reverse_split` | Reverse stock split |
| `cash_dividend` | Cash dividend in VND |
| `stock_dividend` | Stock dividend (e.g., 10% = 10 new shares per 100 held) |
| `bonus_issue` | Bonus shares |
| `rights_issue` | Rights offering at subscription price |

## License

MIT
