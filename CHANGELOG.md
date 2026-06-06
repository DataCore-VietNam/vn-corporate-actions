# Changelog

All notable changes to this project will be documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0](https://github.com/DataCore-VietNam/vn-corporate-actions/compare/v0.2.0...v0.3.0) (2026-06-06)


### Features

* add comprehensive VN corporate-action types and tidy tooling ([ec440b6](https://github.com/DataCore-VietNam/vn-corporate-actions/commit/ec440b618badd3ba887e395a4b308a4128b4c1a3))


### Bug Fixes

* CI failures and configuration ([364c079](https://github.com/DataCore-VietNam/vn-corporate-actions/commit/364c0795e56f28dac91f66f6153bbbb4b1b63096))

## [0.1.0] - 2026-05-29

Initial release. Adjuster for Split / ReverseSplit / CashDividend / StockDividend / BonusIssue / RightsIssue. Backward-adjusted prices and volumes. Multi-action stacking. DataFrame integration. 25 tests.

[0.1.0]: https://github.com/DataCore-VietNam/vn-corporate-actions/releases/tag/v0.1.0

## [0.2.0] - 2026-06-05

Added six corporate-action types for fuller coverage of Vietnamese equities:
`special_cash_dividend`, `return_of_capital`, `spinoff`, `par_value_change`,
`esop_issuance`, and `ticker_change`. Each ships with a convenience helper on
`Adjuster`, backward price/volume math, and tests (47 total). Also: added a
mypy configuration plus `pandas-stubs`, fixed the `Adjuster.__iter__` return
annotation, tightened ticker validation, and cleaned up formatting so the type
check and formatter both run clean.

[0.2.0]: https://github.com/DataCore-VietNam/vn-corporate-actions/releases/tag/v0.2.0
