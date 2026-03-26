from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def value_from_returns(log_returns: pd.Series, initial: float = 1.0) -> pd.Series:
    return initial * np.exp(log_returns.cumsum())


def max_drawdown(value_series: pd.Series) -> float:
    running_max = value_series.cummax()
    drawdown = value_series / running_max - 1.0
    return float(drawdown.min())


def compute_metrics(value_series: pd.Series, rf: float = 0.05) -> Dict[str, float]:
    ret = np.log(value_series / value_series.shift(1)).dropna()
    if ret.empty:
        return {
            "Total Return": np.nan,
            "Annualized Return": np.nan,
            "Volatility": np.nan,
            "Sharpe Ratio": np.nan,
            "Max Drawdown": np.nan,
        }

    total_return = float(value_series.iloc[-1] / value_series.iloc[0] - 1.0)
    ann_return = float(np.exp(ret.mean() * 252.0) - 1.0)
    vol = float(ret.std() * np.sqrt(252.0))
    sharpe = float((ann_return - rf) / vol) if vol > 0 else np.nan
    mdd = max_drawdown(value_series)

    return {
        "Total Return": total_return,
        "Annualized Return": ann_return,
        "Volatility": vol,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": mdd,
    }


def metrics_table(values: Dict[str, pd.Series], rf: float = 0.05) -> pd.DataFrame:
    data = {name: compute_metrics(v, rf=rf) for name, v in values.items()}
    return pd.DataFrame(data).T
