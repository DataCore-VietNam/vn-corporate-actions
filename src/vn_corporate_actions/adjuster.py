"""Backwards price-adjustment engine for Vietnamese corporate actions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime

import numpy as np
import pandas as pd

from vn_corporate_actions.actions import (
    Action,
    BonusIssue,
    CashDividend,
    ReverseSplit,
    RightsIssue,
    Split,
    StockDividend,
)


def _to_date(value: str | date | datetime | pd.Timestamp) -> date:
    """Coerce common date-ish inputs to :class:`datetime.date`."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise TypeError(f"Cannot coerce {value!r} ({type(value).__name__}) to a date.")


class Adjuster:
    """Registry of corporate actions with backwards-adjustment helpers.

    Typical usage::

        adj = Adjuster()
        adj.add_split("VNM", "2023-08-15", ratio=2.0)
        adj.add_cash_dividend("VNM", "2024-06-12", amount=2900)
        adjusted = adj.adjust_prices(df, price_col="close")

    The backward-adjustment convention used here is the standard one:
    historical prices on dates strictly *before* an ex-date are scaled
    so that the time series is continuous across the action; prices on
    or after the ex-date are left untouched.
    """

    def __init__(self) -> None:
        self._actions: dict[str, list[Action]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(self, action: Action) -> None:
        """Register a fully constructed :class:`Action`."""
        self._actions[action.ticker].append(action)

    def add_split(self, ticker: str, ex_date: str | date, ratio: float) -> None:
        """Register a forward split (e.g. ``ratio=2.0`` for 1:2)."""
        self.add(Split(ticker=ticker, ex_date=_to_date(ex_date), ratio=ratio))

    def add_reverse_split(self, ticker: str, ex_date: str | date, ratio: float) -> None:
        """Register a reverse split (e.g. ``ratio=2.0`` for 2:1)."""
        self.add(ReverseSplit(ticker=ticker, ex_date=_to_date(ex_date), ratio=ratio))

    def add_cash_dividend(self, ticker: str, ex_date: str | date, amount: float) -> None:
        """Register a cash dividend (VND per share)."""
        self.add(CashDividend(ticker=ticker, ex_date=_to_date(ex_date), amount=amount))

    def add_stock_dividend(self, ticker: str, ex_date: str | date, ratio: float) -> None:
        """Register a stock dividend (e.g. ``ratio=0.10`` for 10%)."""
        self.add(StockDividend(ticker=ticker, ex_date=_to_date(ex_date), ratio=ratio))

    def add_bonus_issue(self, ticker: str, ex_date: str | date, ratio: float) -> None:
        """Register a bonus share issue (e.g. ``ratio=0.20`` for 20%)."""
        self.add(BonusIssue(ticker=ticker, ex_date=_to_date(ex_date), ratio=ratio))

    def add_rights_issue(
        self,
        ticker: str,
        ex_date: str | date,
        ratio: float,
        subscription_price: float,
    ) -> None:
        """Register a rights issue at ``subscription_price`` (VND)."""
        self.add(
            RightsIssue(
                ticker=ticker,
                ex_date=_to_date(ex_date),
                ratio=ratio,
                subscription_price=subscription_price,
            )
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def actions_for(self, ticker: str) -> list[Action]:
        """Return this ticker's registered actions, sorted by ex-date."""
        return sorted(self._actions.get(ticker, []), key=lambda a: a.ex_date)

    def tickers(self) -> list[str]:
        """All tickers with at least one registered action."""
        return sorted(self._actions.keys())

    # ------------------------------------------------------------------
    # Adjustment math
    # ------------------------------------------------------------------

    def _factor_for_action(
        self,
        action: Action,
        prior_close: float | None,
    ) -> float:
        """Compute the per-action backward multiplier applied to dates < ex.

        Returns the *price* factor; volume scaling is the reciprocal for
        share-count actions and 1.0 for cash dividends.
        """
        if isinstance(action, Split):
            return 1.0 / action.ratio
        if isinstance(action, ReverseSplit):
            return action.ratio
        if isinstance(action, StockDividend):
            return 1.0 / (1.0 + action.ratio)
        if isinstance(action, BonusIssue):
            return 1.0 / (1.0 + action.ratio)
        if isinstance(action, CashDividend):
            if prior_close is None or prior_close <= 0:
                # No reference close available — skip rather than divide by zero.
                return 1.0
            return (prior_close - action.amount) / prior_close
        if isinstance(action, RightsIssue):
            if prior_close is None or prior_close <= 0:
                return 1.0
            theoretical = (prior_close + action.ratio * action.subscription_price) / (
                1.0 + action.ratio
            )
            return theoretical / prior_close
        raise TypeError(f"Unknown action type: {type(action).__name__}")

    @staticmethod
    def _volume_factor_for_action(action: Action) -> float:
        """Per-action backward multiplier applied to *volumes* on dates < ex."""
        if isinstance(action, Split):
            return action.ratio
        if isinstance(action, ReverseSplit):
            return 1.0 / action.ratio
        if isinstance(action, (StockDividend, BonusIssue, RightsIssue)):
            ratio = action.ratio  # type: ignore[attr-defined]
            return 1.0 + ratio
        if isinstance(action, CashDividend):
            return 1.0
        raise TypeError(f"Unknown action type: {type(action).__name__}")

    def adjustment_factor(
        self,
        ticker: str,
        on_date: str | date,
        prior_closes: dict[date, float] | None = None,
    ) -> float:
        """Cumulative backward price-adjustment factor effective on ``on_date``.

        ``on_date`` is the historical trading day whose price we want to
        adjust. The factor is the product of every action factor whose
        ex-date is strictly *after* ``on_date``. For dates on or after the
        most recent ex-date, the factor is ``1.0``.

        ``prior_closes`` maps ex-date to the close on the trading day
        immediately before — required for accurate cash-dividend and
        rights-issue factors. Other action types ignore it.
        """
        target = _to_date(on_date)
        prior_closes = prior_closes or {}
        factor = 1.0
        for action in self.actions_for(ticker):
            if action.ex_date > target:
                factor *= self._factor_for_action(action, prior_closes.get(action.ex_date))
        return factor

    # ------------------------------------------------------------------
    # DataFrame / array adjustment
    # ------------------------------------------------------------------

    def adjust_series(
        self,
        ticker: str,
        dates: Sequence[str | date | datetime | pd.Timestamp],
        prices: Sequence[float],
    ) -> np.ndarray:
        """Backward-adjust an aligned ``(dates, prices)`` pair for one ticker.

        Returns a NumPy array of adjusted prices. ``dates`` and ``prices``
        must be the same length; ``dates`` need not be pre-sorted.
        """
        if len(dates) != len(prices):
            raise ValueError("dates and prices must have the same length")

        normalized = [_to_date(d) for d in dates]
        price_arr = np.asarray(prices, dtype=float)
        prior_closes = self._prior_closes(ticker, normalized, price_arr)

        actions = self.actions_for(ticker)
        if not actions:
            return price_arr.copy()

        factors = np.ones_like(price_arr)
        for action in actions:
            per_action = self._factor_for_action(action, prior_closes.get(action.ex_date))
            mask = np.array([d < action.ex_date for d in normalized])
            factors[mask] *= per_action
        return price_arr * factors

    def adjust_prices(
        self,
        df: pd.DataFrame,
        ticker_col: str = "ticker",
        date_col: str = "trade_date",
        price_col: str = "close",
        volume_col: str | None = None,
    ) -> pd.DataFrame:
        """Return a copy of ``df`` with backward-adjusted price (and volume).

        The adjusted price column overwrites ``price_col`` in the returned
        frame; ``volume_col`` is overwritten in place too when provided.
        The original DataFrame is not mutated.

        Multiple tickers are handled independently. Rows with tickers that
        have no registered actions pass through unchanged.
        """
        for col in (ticker_col, date_col, price_col):
            if col not in df.columns:
                raise KeyError(f"Required column {col!r} not in DataFrame")
        if volume_col is not None and volume_col not in df.columns:
            raise KeyError(f"Volume column {volume_col!r} not in DataFrame")

        out = df.copy()
        for ticker, group in out.groupby(ticker_col, sort=False):
            actions = self.actions_for(str(ticker))
            if not actions:
                continue

            dates = [_to_date(d) for d in group[date_col]]
            prices = group[price_col].to_numpy(dtype=float)
            prior_closes = self._prior_closes(str(ticker), dates, prices)

            price_factor = np.ones(len(group), dtype=float)
            volume_factor = np.ones(len(group), dtype=float)
            for action in actions:
                pf = self._factor_for_action(action, prior_closes.get(action.ex_date))
                vf = self._volume_factor_for_action(action)
                mask = np.array([d < action.ex_date for d in dates])
                price_factor[mask] *= pf
                volume_factor[mask] *= vf

            out.loc[group.index, price_col] = prices * price_factor
            if volume_col is not None:
                volumes = group[volume_col].to_numpy(dtype=float)
                out.loc[group.index, volume_col] = volumes * volume_factor
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _prior_closes(
        self,
        ticker: str,
        dates: Sequence[date],
        prices: np.ndarray,
    ) -> dict[date, float]:
        """Look up the close on the trading day immediately before each ex-date.

        Used for cash dividends and rights issues. Returns an empty mapping
        if no such close is available (e.g. the ex-date precedes the data).
        """
        actions = self.actions_for(ticker)
        needs_prior = [
            a for a in actions if isinstance(a, (CashDividend, RightsIssue))
        ]
        if not needs_prior:
            return {}

        order = np.argsort(dates)
        sorted_dates = [dates[i] for i in order]
        sorted_prices = prices[order]

        result: dict[date, float] = {}
        for action in needs_prior:
            # Largest date strictly less than ex_date.
            prior_idx = None
            for i, d in enumerate(sorted_dates):
                if d < action.ex_date:
                    prior_idx = i
                else:
                    break
            if prior_idx is not None:
                result[action.ex_date] = float(sorted_prices[prior_idx])
        return result

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return sum(len(v) for v in self._actions.values())

    def __iter__(self) -> Iterable[Action]:
        for ticker in sorted(self._actions):
            yield from self.actions_for(ticker)

    def __repr__(self) -> str:
        return f"Adjuster(tickers={len(self._actions)}, actions={len(self)})"
