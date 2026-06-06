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

| Type | Helper | Price effect on dates before ex-date |
|------|--------|--------------------------------------|
| `split` | `add_split` | Price divided by ratio, volume multiplied |
| `reverse_split` | `add_reverse_split` | Price multiplied by ratio, volume divided |
| `stock_dividend` | `add_stock_dividend` | Price scaled by `1/(1+ratio)` (e.g. 10% = 10 new shares per 100 held) |
| `bonus_issue` | `add_bonus_issue` | Same math as stock dividend; funded from reserves |
| `par_value_change` | `add_par_value_change` | Price scaled by `new_par/old_par` (redenomination) |
| `cash_dividend` | `add_cash_dividend` | Price scaled by `(P - amount)/P` |
| `special_cash_dividend` | `add_special_cash_dividend` | Same math as cash dividend; flagged as one-off |
| `return_of_capital` | `add_return_of_capital` | Same math as cash dividend; capital returned in cash |
| `spinoff` | `add_spinoff` | Price scaled by `(P - value_per_share)/P` |
| `rights_issue` | `add_rights_issue` | Theoretical ex-rights price (TERP) over prior close |
| `esop_issuance` | `add_esop_issuance` | TERP-style dilution at the ESOP issue price |
| `ticker_change` | `add_ticker_change` | None (metadata only) |

`P` is the official close on the trading day immediately before the ex-date.
Cash, spin-off and rights/ESOP factors need that prior close, which the
library reads from the price series at adjustment time.

## License

MIT
