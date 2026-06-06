"""Pydantic-validation tests for each action type."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from vn_corporate_actions import (
    BonusIssue,
    CashDividend,
    ESOPIssuance,
    ParValueChange,
    ReturnOfCapital,
    ReverseSplit,
    RightsIssue,
    SpecialCashDividend,
    Spinoff,
    Split,
    StockDividend,
    TickerChange,
)


class TestSplit:
    def test_basic(self) -> None:
        s = Split(ticker="VNM", ex_date=date(2023, 8, 15), ratio=2.0)
        assert s.ticker == "VNM"
        assert s.kind == "split"
        assert s.ratio == 2.0

    def test_rejects_non_positive_ratio(self) -> None:
        with pytest.raises(ValidationError):
            Split(ticker="VNM", ex_date=date(2023, 8, 15), ratio=0)


class TestReverseSplit:
    def test_basic(self) -> None:
        rs = ReverseSplit(ticker="ABC", ex_date=date(2024, 1, 1), ratio=5.0)
        assert rs.kind == "reverse_split"
        assert rs.ratio == 5.0


class TestCashDividend:
    def test_basic(self) -> None:
        cd = CashDividend(ticker="VNM", ex_date=date(2024, 6, 12), amount=2900)
        assert cd.kind == "cash_dividend"
        assert cd.amount == 2900

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            CashDividend(ticker="VNM", ex_date=date(2024, 6, 12), amount=-100)


class TestStockDividend:
    def test_basic(self) -> None:
        sd = StockDividend(ticker="HPG", ex_date=date(2023, 5, 10), ratio=0.10)
        assert sd.kind == "stock_dividend"
        assert sd.ratio == 0.10


class TestBonusIssue:
    def test_basic(self) -> None:
        bi = BonusIssue(ticker="HPG", ex_date=date(2023, 7, 20), ratio=0.20)
        assert bi.kind == "bonus_issue"
        assert bi.ratio == 0.20


class TestRightsIssue:
    def test_basic(self) -> None:
        ri = RightsIssue(
            ticker="VIC",
            ex_date=date(2023, 9, 1),
            ratio=0.20,
            subscription_price=10_000,
        )
        assert ri.kind == "rights_issue"
        assert ri.subscription_price == 10_000

    def test_rejects_negative_sub_price(self) -> None:
        with pytest.raises(ValidationError):
            RightsIssue(
                ticker="VIC",
                ex_date=date(2023, 9, 1),
                ratio=0.20,
                subscription_price=-1,
            )


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        Split(ticker="VNM", ex_date=date(2023, 8, 15), ratio=2.0, mystery=1)  # type: ignore[call-arg]


def test_ex_date_accepts_iso_string() -> None:
    # Pydantic 2 will coerce a YYYY-MM-DD string to date.
    s = Split(ticker="VNM", ex_date="2023-08-15", ratio=2.0)  # type: ignore[arg-type]
    assert s.ex_date == date(2023, 8, 15)


class TestParValueChange:
    def test_basic(self) -> None:
        pv = ParValueChange(ticker="VNM", ex_date=date(2024, 3, 1), old_par=10_000, new_par=5_000)
        assert pv.kind == "par_value_change"
        assert pv.old_par == 10_000
        assert pv.new_par == 5_000

    def test_rejects_non_positive_par(self) -> None:
        with pytest.raises(ValidationError):
            ParValueChange(ticker="VNM", ex_date=date(2024, 3, 1), old_par=10_000, new_par=0)


class TestSpecialCashDividend:
    def test_basic(self) -> None:
        sd = SpecialCashDividend(ticker="VNM", ex_date=date(2024, 6, 12), amount=8_000)
        assert sd.kind == "special_cash_dividend"
        assert sd.amount == 8_000

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValidationError):
            SpecialCashDividend(ticker="VNM", ex_date=date(2024, 6, 12), amount=-1)


class TestReturnOfCapital:
    def test_basic(self) -> None:
        rc = ReturnOfCapital(ticker="VNM", ex_date=date(2024, 6, 12), amount=3_000)
        assert rc.kind == "return_of_capital"
        assert rc.amount == 3_000


class TestSpinoff:
    def test_basic(self) -> None:
        sp = Spinoff(ticker="VIC", ex_date=date(2024, 4, 1), value_per_share=12_000)
        assert sp.kind == "spinoff"
        assert sp.value_per_share == 12_000

    def test_rejects_non_positive_value(self) -> None:
        with pytest.raises(ValidationError):
            Spinoff(ticker="VIC", ex_date=date(2024, 4, 1), value_per_share=0)


class TestESOPIssuance:
    def test_basic(self) -> None:
        es = ESOPIssuance(ticker="FPT", ex_date=date(2024, 2, 1), ratio=0.05, issue_price=10_000)
        assert es.kind == "esop_issuance"
        assert es.ratio == 0.05
        assert es.issue_price == 10_000

    def test_allows_free_grant(self) -> None:
        es = ESOPIssuance(ticker="FPT", ex_date=date(2024, 2, 1), ratio=0.05, issue_price=0)
        assert es.issue_price == 0

    def test_rejects_negative_issue_price(self) -> None:
        with pytest.raises(ValidationError):
            ESOPIssuance(ticker="FPT", ex_date=date(2024, 2, 1), ratio=0.05, issue_price=-1)


class TestTickerChange:
    def test_basic(self) -> None:
        tc = TickerChange(ticker="MSN", ex_date=date(2023, 1, 1), new_ticker="MSN2")
        assert tc.kind == "ticker_change"
        assert tc.new_ticker == "MSN2"

    def test_rejects_empty_new_ticker(self) -> None:
        with pytest.raises(ValidationError):
            TickerChange(ticker="MSN", ex_date=date(2023, 1, 1), new_ticker="")


def test_empty_ticker_rejected() -> None:
    with pytest.raises(ValidationError):
        Split(ticker="", ex_date=date(2023, 8, 15), ratio=2.0)
