from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class SplitData:
    train_returns: pd.DataFrame
    test_returns: pd.DataFrame
    train_prices: pd.DataFrame
    test_prices: pd.DataFrame
    split_dates: dict


def clean_prices(prices: pd.DataFrame, min_non_na_ratio: float = 0.85) -> pd.DataFrame:
    px = prices.copy().sort_index()
    px = px.loc[~px.index.duplicated(keep="first")]

    keep_cols = px.columns[px.notna().mean() >= min_non_na_ratio]
    px = px[keep_cols]

    px = px.ffill().bfill()
    px = px.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="any")
    return px


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    returns = np.log(prices / prices.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="all")
    return returns


def annualize_stats(returns: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame, pd.Series]:
    mu = returns.mean() * 252.0
    cov = returns.cov() * 252.0
    downside = np.sqrt(np.mean(np.square(np.minimum(returns, 0.0)), axis=0)) * np.sqrt(252.0)
    downside = pd.Series(downside, index=returns.columns)
    return mu, cov, downside


def time_series_split(prices: pd.DataFrame, train_years: int = 10, test_years: int = 5, test_end_date=None) -> SplitData:
    if prices.empty:
        raise ValueError("Price frame is empty.")

    returns = log_returns(prices)
    start = returns.index.min()
    train_end = start + pd.DateOffset(years=train_years)
    
    # Use test_end_date if provided, otherwise calculate from test_years
    if test_end_date is not None:
        test_end = pd.Timestamp(test_end_date)
    else:
        test_end = train_end + pd.DateOffset(years=test_years)

    train_returns = returns.loc[(returns.index >= start) & (returns.index < train_end)].copy()
    test_returns = returns.loc[(returns.index >= train_end) & (returns.index < test_end)].copy()

    train_prices = prices.loc[(prices.index >= prices.index.min()) & (prices.index < train_end)].copy()
    test_prices = prices.loc[(prices.index >= train_end) & (prices.index < test_end)].copy()

    if train_returns.empty or test_returns.empty:
        raise RuntimeError("Not enough data for strict 10y train and 5y test split.")

    return SplitData(
        train_returns=train_returns,
        test_returns=test_returns,
        train_prices=train_prices,
        test_prices=test_prices,
        split_dates={
            "start": start,
            "train_end": train_end,
            "test_end": test_end,
        },
    )
