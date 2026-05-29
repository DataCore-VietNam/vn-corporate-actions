"""Pydantic-validation tests for each action type."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from vn_corporate_actions import (
    BonusIssue,
    CashDividend,
    ReverseSplit,
    RightsIssue,
    Split,
    StockDividend,
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
