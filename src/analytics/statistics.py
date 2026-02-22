# src/analytics/statistics.py
from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def add_vix_deviation_indicators(
    df: pd.DataFrame,
    window: int = 252,
    price_col: str = "close",
) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # FIX: Added min_periods=1 to rolling, so deviation_pct from day 1 (mean=price, dev=0 if n=1)
    df["rolling_mean"] = df[price_col].rolling(window, min_periods=1).mean()
    df["deviation_pct"] = (df[price_col] / df["rolling_mean"] - 1) * 100
    return df.reset_index(drop=True)  # No dropna, keep all rows (early dev=0 ok)


def get_deviation_levels(
    df: pd.DataFrame,
    col: str = "deviation_pct",
    sigma_levels: Optional[Iterable[int]] = None,
) -> Dict[str, float]:
    if df is None or df.empty or col not in df.columns:
        return None
     
    clean_dev = df[col].dropna()
    if clean_dev.empty:  # FIX: Lowered to empty check (allow len=1)
        return None
     
    sigma_levels = list(sigma_levels)
    mean = float(clean_dev.mean())
    std = float(clean_dev.std(ddof=0))  # ddof=0 for population std, 0 when n=1
    levels: Dict[str, float] = {"mean": mean}
    for s in sigma_levels:
        levels[f"+{s}σ"] = mean + s * std
        levels[f"-{s}σ"] = mean - s * std
    logger.debug(f"Deviation levels for {col}: {levels}")

    return levels

def get_quantile_thresholds(series: pd.Series, window: int = 504) -> Optional[Dict[str, float]]:
    if series is None:
        return None
     
    clean_series = series.dropna()
    if clean_series.empty:  # FIX: Lowered to empty check (allow len=1)
        return None
     
    lookback = clean_series.iloc[-window:]
    q = lookback.quantile([0.05, 0.10, 0.90, 0.95])
     
    return {
        "p5": round(float(q.loc[0.05]), 2),
        "p10": round(float(q.loc[0.10]), 2),
        "p90": round(float(q.loc[0.90]), 2),
        "p95": round(float(q.loc[0.95]), 2),
    }


def calculate_z_score(
    df: pd.DataFrame,
    column: str = "Comm_Net", # ← ИЗМЕНЕНО: теперь Commercial
    window: int = 104,
) -> pd.DataFrame:
    """COT Z-Score по коммерсантам (smart money)."""
    df = df.copy()
    # FIX: Added min_periods=1, std(ddof=0)=0 for n=1, Z=0
    roll_mean = df[column].rolling(window, min_periods=1).mean()
    roll_std = df[column].rolling(window, min_periods=1).std(ddof=0)
    df["Z_Score_Comm"] = (df[column] - roll_mean) / roll_std
    df["Z_Score_Comm"] = df["Z_Score_Comm"].fillna(0.0)  # Explicitly set NaN (if any) to 0
    return df.reset_index(drop=True)


def calculate_cot_composite(
    comm_idx: float,
    large_inv_idx: float,
    z_comm: float,                     # ← теперь Commercial Z-Score
    thresholds: Dict[str, float],
) -> tuple[float, str]:
    """COT Composite с Z-score коммерсантов (высокий Z = bullish)."""
    score = 0.0
    parts: list[str] = []

    # Commercial Index
    if comm_idx >= thresholds["p95"]:
        score += 2.2
        parts.append("Comm ≥95p → Strong Bull")
    elif comm_idx >= thresholds["p90"]:
        score += 1.3
        parts.append("Comm ≥90p → Bull")
    elif comm_idx <= thresholds["p5"] or comm_idx <= 0:
        score -= 2.2
        parts.append("Comm ≤5p/≤0 → Strong Bear")
    elif comm_idx <= thresholds["p10"]:
        score -= 1.3
        parts.append("Comm ≤10p → Bear")

    if large_inv_idx <= thresholds["p5"]:
        parts.append("LargeInv ≤5p (note)")

    # Commercial Z-Score (smart money)
    if z_comm >= 3.0:
        score += 2.0
        parts.append("Comm Z ≥3.0 → Strong Bull boost")
    elif z_comm <= -3.0:
        score -= 1.8
        parts.append("Comm Z ≤-3.0 → Strong Bear penalty")

    cot_score = round(score, 2)
    cot_text = " | ".join(parts) if parts else "COT neutral"
    logger.debug(f"COT composite score: {cot_score}, text: {cot_text}")
    return cot_score, cot_text


# Остальные функции (validation, sharpe и т.д.) без изменений
def compute_max_drawdown(equity: pd.Series) -> float:
    if equity is None or len(equity) < 2:
        return 0.0
    eq = pd.to_numeric(equity, errors="coerce").astype(float).dropna()
    if eq.empty:
        return 0.0
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    max_dd = float(dd.min())
    logger.debug(f"Max drawdown: {max_dd}")
    return max_dd


def compute_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = pd.to_numeric(returns, errors="coerce").astype(float).dropna()
    if len(r) < 2:
        return 0.0
    std = float(r.std(ddof=0))
    if std == 0.0:
        return 0.0
    sharpe = float((r.mean() / std) * np.sqrt(periods_per_year))
    logger.debug(f"Sharpe: {sharpe}")
    return sharpe


def _price_series(df_price: pd.DataFrame) -> pd.Series:
    if df_price is None or df_price.empty:
        return pd.Series(dtype=float)
    tmp = df_price[["date", "close"]].copy()
    tmp["date"] = pd.to_datetime(tmp["date"]).dt.normalize()
    tmp = tmp.sort_values("date")
    return tmp.set_index("date")["close"].astype(float)


def forward_return(price: pd.Series, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> float | None:
    if price is None or price.empty:
        return None
    start_px = price.asof(start_ts)
    end_px = price.asof(end_ts)
    if pd.isna(start_px) or pd.isna(end_px) or start_px == 0:
        return None
    fwd_ret = float(end_px / start_px - 1.0)
    logger.debug(f"Forward return from {start_ts} to {end_ts}: {fwd_ret}")
    return fwd_ret


def trend_accuracy(
    signals: pd.DataFrame,
    df_price: pd.DataFrame,
    horizon_months: int,
    bullish_label: str = "Bullish Trend",
    bearish_label: str = "Bearish Trend",
) -> Tuple[float, float, Dict[str, int]]:
    if signals is None or signals.empty or df_price is None or df_price.empty:
        return 0.0, 0.0, {"bull_correct": 0, "bull_wrong": 0, "bear_correct": 0, "bear_wrong": 0, "evaluated": 0}

    sig = signals.copy()
    sig["date"] = pd.to_datetime(sig["date"]).dt.normalize()
    sig = sig.sort_values("date").reset_index(drop=True)

    price = _price_series(df_price)
    if price.empty:
        return 0.0, 0.0, {"bull_correct": 0, "bull_wrong": 0, "bear_correct": 0, "bear_wrong": 0, "evaluated": 0}

    total = len(sig)
    evaluated = 0
    correct = 0
    bull_correct = bull_wrong = bear_correct = bear_wrong = 0

    for _, row in sig.iterrows():
        verdict = str(row.get("verdict", ""))
        if verdict not in (bullish_label, bearish_label):
            continue

        start_ts = pd.Timestamp(row["date"]).normalize()
        end_ts = (start_ts + pd.DateOffset(months=int(horizon_months))).normalize()

        fr = forward_return(price, start_ts, end_ts)
        if fr is None:
            continue

        evaluated += 1
        if verdict == bullish_label:
            if fr > 0:
                correct += 1
                bull_correct += 1
            elif fr < 0:
                bull_wrong += 1
        else:
            if fr < 0:
                correct += 1
                bear_correct += 1
            elif fr > 0:
                bear_wrong += 1

    accuracy = float(correct / evaluated) if evaluated > 0 else 0.0
    coverage = float(evaluated / total) if total > 0 else 0.0

    confusion = {
        "bull_correct": int(bull_correct),
        "bull_wrong": int(bull_wrong),
        "bear_correct": int(bear_correct),
        "bear_wrong": int(bear_wrong),
        "evaluated": int(evaluated),
    }
    logger.debug(f"Trend accuracy: {accuracy}, coverage: {coverage}, confusion: {confusion}")
    return accuracy, coverage, confusion