"""Pydantic models for Vietnamese equity corporate-action types.

The catalogue below aims to cover the corporate actions that actually move a
listed Vietnamese share price (HOSE / HNX / UPCoM) and therefore require a
backward adjustment to keep a historical price series continuous:

Share-count actions (price scaled by a pure ratio, no market data needed)
    Split, ReverseSplit, StockDividend, BonusIssue, ParValueChange

Cash-outflow actions (price reduced by a per-share cash amount; needs the
prior close)
    CashDividend, SpecialCashDividend, ReturnOfCapital, Spinoff

Dilution actions (new shares sold below market; needs the prior close)
    RightsIssue, ESOPIssuance

Metadata-only actions (no price effect, tracked for completeness)
    TickerChange

Every action carries a ``ticker`` and an ``ex_date``. For backward
adjustment, prices on dates strictly *before* ``ex_date`` are scaled by the
action's factor; prices on or after ``ex_date`` are left unchanged.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Action(BaseModel):
    """Base corporate action.

    All actions carry a ticker symbol and an ex-date -- the trading day on
    which the action is reflected in the market price. For backwards price
    adjustment, dates strictly before ``ex_date`` are scaled by the action's
    factor; dates on or after ``ex_date`` are left unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., min_length=1, description="Equity ticker symbol, e.g. 'VNM'.")
    ex_date: date = Field(..., description="Ex-date (first trading day priced ex-action).")
    kind: str = Field(..., description="Discriminator tag for the action type.")


# ----------------------------------------------------------------------
# Share-count actions: price scaled by a deterministic ratio.
# ----------------------------------------------------------------------


class Split(Action):
    """Forward stock split.

    A ``ratio`` of ``2.0`` means a 1:2 split -- one old share becomes two
    new shares. Pre-split prices are divided by ``ratio``; pre-split
    volumes are multiplied by ``ratio``.
    """

    kind: Literal["split"] = "split"
    ratio: float = Field(..., gt=0, description="New shares per old share (e.g. 2.0 for 1:2).")


class ReverseSplit(Action):
    """Reverse stock split (share consolidation).

    A ``ratio`` of ``2.0`` means 2:1 reverse -- two old shares become one
    new share. Pre-split prices are multiplied by ``ratio``; pre-split
    volumes are divided by ``ratio``.
    """

    kind: Literal["reverse_split"] = "reverse_split"
    ratio: float = Field(..., gt=0, description="Old shares consolidated into one new share.")


class StockDividend(Action):
    """Stock dividend, expressed as a fraction of existing holdings.

    A ``ratio`` of ``0.10`` means 10 new shares per 100 held. Pre-action
    prices are scaled by ``1 / (1 + ratio)``; volumes by ``(1 + ratio)``.
    Very common in Vietnam, often paid out of retained earnings.
    """

    kind: Literal["stock_dividend"] = "stock_dividend"
    ratio: float = Field(..., gt=0, description="New shares per share held.")


class BonusIssue(Action):
    """Bonus share issue.

    Mathematically identical to :class:`StockDividend` -- bonus shares as a
    fraction of holdings. Modeled separately because Vietnamese filings
    distinguish the two (bonus shares are funded from share premium or
    other equity reserves rather than retained earnings).
    """

    kind: Literal["bonus_issue"] = "bonus_issue"
    ratio: float = Field(..., gt=0, description="Bonus shares per share held.")


class ParValueChange(Action):
    """Change in par (face) value, with an offsetting change in share count.

    Vietnamese listed shares carry a par value (historically VND 10,000). A
    redenomination that halves par while doubling the share count is
    economically a 1:2 split. The price factor is ``new_par / old_par`` and
    the volume factor is its reciprocal.
    """

    kind: Literal["par_value_change"] = "par_value_change"
    old_par: float = Field(..., gt=0, description="Par value before the change (VND).")
    new_par: float = Field(..., gt=0, description="Par value after the change (VND).")


# ----------------------------------------------------------------------
# Cash-outflow actions: price reduced by a per-share cash amount.
# ----------------------------------------------------------------------


class CashDividend(Action):
    """Cash dividend in VND per share.

    The backward adjustment factor is ``(P - amount) / P`` where ``P`` is
    the official close on the trading day immediately preceding ``ex_date``.
    The prior close is looked up from the price DataFrame at adjustment
    time; it is not stored on the action.
    """

    kind: Literal["cash_dividend"] = "cash_dividend"
    amount: float = Field(..., gt=0, description="Dividend amount in VND per share.")


class SpecialCashDividend(Action):
    """One-off / special cash dividend in VND per share.

    Economically identical to :class:`CashDividend` for price-adjustment
    purposes (factor ``(P - amount) / P``), but tagged separately so that
    extraordinary distributions can be distinguished from the regular
    dividend stream in reporting.
    """

    kind: Literal["special_cash_dividend"] = "special_cash_dividend"
    amount: float = Field(..., gt=0, description="Special dividend amount in VND per share.")


class ReturnOfCapital(Action):
    """Return of capital / capital reduction paid in cash to shareholders.

    Treated like a cash dividend for price adjustment (factor
    ``(P - amount) / P``) because it is a per-share cash outflow on the
    ex-date. Kept distinct from :class:`CashDividend` because the
    accounting and tax treatment differ.
    """

    kind: Literal["return_of_capital"] = "return_of_capital"
    amount: float = Field(..., gt=0, description="Capital returned in VND per share.")


class Spinoff(Action):
    """Spin-off / demerger distributing a subsidiary to shareholders.

    On the ex-date the parent price drops by the per-share value of the
    distributed entity. The backward factor is
    ``(P - value_per_share) / P`` where ``P`` is the close immediately
    before ``ex_date`` (looked up from the price DataFrame at adjustment
    time).
    """

    kind: Literal["spinoff"] = "spinoff"
    value_per_share: float = Field(
        ..., gt=0, description="Value distributed per parent share, in VND."
    )


# ----------------------------------------------------------------------
# Dilution actions: new shares sold below market.
# ----------------------------------------------------------------------


class RightsIssue(Action):
    """Rights offering at a fixed subscription price.

    A ``ratio`` of ``0.20`` with ``subscription_price=10_000`` means
    shareholders may buy 1 new share at VND 10,000 for every 5 held.

    The backward adjustment factor is the theoretical ex-rights price
    divided by the prior close::

        T = (P + ratio * subscription_price) / (1 + ratio)
        factor = T / P

    where ``P`` is the close immediately before ``ex_date`` (looked up
    from the price DataFrame at adjustment time).
    """

    kind: Literal["rights_issue"] = "rights_issue"
    ratio: float = Field(..., gt=0, description="New rights shares per share held.")
    subscription_price: float = Field(..., gt=0, description="Subscription price in VND.")


class ESOPIssuance(Action):
    """Employee stock ownership plan (ESOP) issuance below market price.

    Common in Vietnam and dilutive in the same way as a rights issue:
    new shares are created at an ``issue_price`` typically below market.
    A ``ratio`` of ``0.05`` means 5 new ESOP shares per 100 outstanding.
    Adjustment math mirrors :class:`RightsIssue`::

        T = (P + ratio * issue_price) / (1 + ratio)
        factor = T / P
    """

    kind: Literal["esop_issuance"] = "esop_issuance"
    ratio: float = Field(..., gt=0, description="New ESOP shares per share outstanding.")
    issue_price: float = Field(
        ..., ge=0, description="ESOP issue price in VND (0 for a free grant)."
    )


# ----------------------------------------------------------------------
# Metadata-only actions: no price effect.
# ----------------------------------------------------------------------


class TickerChange(Action):
    """Ticker / symbol change. No price effect.

    Recorded so a ledger can track symbol history (Vietnamese tickers do
    change). The backward price and volume factors are both ``1.0``.
    """

    kind: Literal["ticker_change"] = "ticker_change"
    new_ticker: str = Field(..., min_length=1, description="The new ticker symbol.")


# Convenience union for code that wants to type-annotate any concrete action.
AnyAction = (
    Split
    | ReverseSplit
    | StockDividend
    | BonusIssue
    | ParValueChange
    | CashDividend
    | SpecialCashDividend
    | ReturnOfCapital
    | Spinoff
    | RightsIssue
    | ESOPIssuance
    | TickerChange
)
