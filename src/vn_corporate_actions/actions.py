"""Pydantic models for Vietnamese equity corporate-action types."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Action(BaseModel):
    """Base corporate action.

    All actions carry a ticker symbol and an ex-date — the trading day on
    which the action is reflected in the market price. For backwards price
    adjustment, dates strictly before ``ex_date`` are scaled by the action's
    factor; dates on or after ``ex_date`` are left unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., description="Equity ticker symbol, e.g. 'VNM'.")
    ex_date: date = Field(..., description="Ex-date (first trading day priced ex-action).")
    kind: str = Field(..., description="Discriminator tag for the action type.")


class Split(Action):
    """Forward stock split.

    A ``ratio`` of ``2.0`` means a 1:2 split — one old share becomes two
    new shares. Pre-split prices are divided by ``ratio``; pre-split
    volumes are multiplied by ``ratio``.
    """

    kind: Literal["split"] = "split"
    ratio: float = Field(..., gt=0, description="New shares per old share (e.g. 2.0 for 1:2).")


class ReverseSplit(Action):
    """Reverse stock split.

    A ``ratio`` of ``2.0`` means 2:1 reverse — two old shares become one
    new share. Pre-split prices are multiplied by ``ratio``; pre-split
    volumes are divided by ``ratio``.
    """

    kind: Literal["reverse_split"] = "reverse_split"
    ratio: float = Field(..., gt=0, description="Old shares consolidated into one new share.")


class CashDividend(Action):
    """Cash dividend in VND per share.

    The backward adjustment factor is ``(P - amount) / P`` where ``P`` is
    the official close on the trading day immediately preceding ``ex_date``.
    The prior close is looked up from the price DataFrame at adjustment
    time; it is not stored on the action.
    """

    kind: Literal["cash_dividend"] = "cash_dividend"
    amount: float = Field(..., gt=0, description="Dividend amount in VND per share.")


class StockDividend(Action):
    """Stock dividend, expressed as a fraction of existing holdings.

    A ``ratio`` of ``0.10`` means 10 new shares per 100 held. Pre-action
    prices are scaled by ``1 / (1 + ratio)``; volumes by ``(1 + ratio)``.
    """

    kind: Literal["stock_dividend"] = "stock_dividend"
    ratio: float = Field(..., gt=0, description="New shares per share held.")


class BonusIssue(Action):
    """Bonus share issue.

    Mathematically identical to :class:`StockDividend` — bonus shares as a
    fraction of holdings. Modeled separately because Vietnamese filings
    distinguish the two.
    """

    kind: Literal["bonus_issue"] = "bonus_issue"
    ratio: float = Field(..., gt=0, description="Bonus shares per share held.")


class RightsIssue(Action):
    """Rights offering at a fixed subscription price.

    A ``ratio`` of ``0.20`` with ``subscription_price=10_000`` means
    shareholders may buy 1 new share at VND 10,000 for every 5 held.

    The backward adjustment factor is the theoretical ex-rights price
    divided by the prior close:

        T = (P + ratio * subscription_price) / (1 + ratio)
        factor = T / P

    where ``P`` is the close immediately before ``ex_date`` (looked up
    from the price DataFrame at adjustment time).
    """

    kind: Literal["rights_issue"] = "rights_issue"
    ratio: float = Field(..., gt=0, description="New rights shares per share held.")
    subscription_price: float = Field(..., gt=0, description="Subscription price in VND.")


# Convenience union for code that wants to type-annotate any concrete action.
AnyAction = Split | ReverseSplit | CashDividend | StockDividend | BonusIssue | RightsIssue
