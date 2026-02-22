# src/analytics/trend_validation.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd
import logging

from src.analytics.signal_generator import generate_signals
from src.analytics.statistics import compute_max_drawdown, compute_sharpe, trend_accuracy
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


@dataclass
class TrendValidationResult:
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]
    confusion: Dict[str, int]
    signals: pd.DataFrame


def _slice_price(df: pd.DataFrame, start_date=None, end_date=None) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    if start_date is not None:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    return df.reset_index(drop=True)


def run_trend_validation(
    dfs: Dict[str, pd.DataFrame],
    asset: str,
    initial_capital: float,
    start_date=None,
    end_date=None,
) -> TrendValidationResult:
    """
    Compass "backtest": trend validation (hold when Bullish Trend, else cash).
    - No fees, no trailing stop, no intra-month trading.
    - Monthly regime signals from generate_signals (step_days=30 by default).
    """
    logger.debug(f"Running trend validation for {asset}, capital={initial_capital}, start={start_date}, end={end_date}")

    s = get_settings()
    asset_key = asset.lower()

    if asset_key not in dfs or dfs[asset_key] is None or dfs[asset_key].empty:
        logger.warning("No data for asset")
        return TrendValidationResult(pd.DataFrame(), {}, {}, pd.DataFrame())

    df_price = _slice_price(dfs[asset_key], start_date=start_date, end_date=end_date)
    if df_price.empty or len(df_price) < 2:
        logger.warning("Empty price slice")
        return TrendValidationResult(pd.DataFrame(), {}, {}, pd.DataFrame())

    # Monthly signals (already compass-aware).
    signals = generate_signals(dfs, asset=asset)
    logger.debug(f"All signals shape: {signals.shape}")

    if start_date is not None or end_date is not None:
        tmp = signals.copy()
        tmp["date"] = pd.to_datetime(tmp["date"]).dt.normalize()
        if start_date is not None:
            tmp = tmp[tmp["date"] >= pd.to_datetime(start_date)]
        if end_date is not None:
            tmp = tmp[tmp["date"] <= pd.to_datetime(end_date)]
        signals = tmp.reset_index(drop=True)
    logger.debug(f"Filtered signals shape: {signals.shape}")

    if signals.empty:
        # If we can't compute signals, fall back to "cash" curve.
        equity_curve = df_price[["date", "close"]].copy()
        equity_curve["Equity"] = float(initial_capital)
        logger.debug("No signals, fallback to cash curve")
        return TrendValidationResult(
            equity_curve=equity_curve,
            metrics={"total_return": 0.0, "bh_total_return": float(df_price["close"].iloc[-1] / df_price["close"].iloc[0] - 1.0)},
            confusion={},
            signals=signals,
        )

    # Daily position via merge_asof (use last signal <= day)
    daily = df_price[["date", "close"]].copy()
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    daily = daily.sort_values("date").reset_index(drop=True)

    sig = signals[["date", "verdict"]].copy()
    sig["date"] = pd.to_datetime(sig["date"]).dt.normalize()
    sig = sig.sort_values("date").reset_index(drop=True)

    daily = pd.merge_asof(daily, sig, on="date", direction="backward")
    daily["verdict"] = daily["verdict"].fillna("Neutral")
    daily["pos"] = (daily["verdict"] == "Bullish Trend").astype(int)
    logger.debug(f"Daily positions shape: {daily.shape}")

    # Strategy equity
    daily["asset_ret"] = daily["close"].pct_change().fillna(0.0)
    daily["strategy_ret"] = daily["asset_ret"] * daily["pos"]
    daily["Equity"] = float(initial_capital) * (1.0 + daily["strategy_ret"]).cumprod()
    logger.debug(f"Equity calculated")

    equity_curve = daily[["date", "close", "Equity"]].copy()

    # Buy & Hold equity for metrics (chart already overlays)
    bh_equity = float(initial_capital) * (daily["close"] / daily["close"].iloc[0])
    bh_ret = bh_equity.pct_change().fillna(0.0)

    total_return = float(equity_curve["Equity"].iloc[-1] / float(initial_capital) - 1.0)
    bh_total_return = float(daily["close"].iloc[-1] / daily["close"].iloc[0] - 1.0)

    dd = compute_max_drawdown(equity_curve["Equity"])
    bh_dd = compute_max_drawdown(bh_equity)

    dd_reduction = abs(bh_dd) - abs(dd)

    sharpe = compute_sharpe(equity_curve["Equity"].pct_change().fillna(0.0))
    bh_sharpe = compute_sharpe(bh_ret)

    acc, cov, confusion = trend_accuracy(
        signals=signals,
        df_price=df_price,
        horizon_months=int(s.compass.trend_horizon_months),
    )

    metrics = {
        "total_return": total_return,
        "bh_total_return": bh_total_return,
        "max_dd": dd,
        "bh_max_dd": bh_dd,
        "dd_reduction": dd_reduction,
        "sharpe": sharpe,
        "bh_sharpe": bh_sharpe,
        "trend_accuracy": acc,
        "trend_coverage": cov,
        "horizon_months": float(s.compass.trend_horizon_months),
    }
    logger.debug(f"Metrics: {metrics}")

    return TrendValidationResult(equity_curve=equity_curve, metrics=metrics, confusion=confusion, signals=signals)