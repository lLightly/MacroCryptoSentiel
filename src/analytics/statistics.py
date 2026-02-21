from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd


def add_vix_deviation_indicators(
    df: pd.DataFrame,
    window: int = 252,
    price_col: str = "close",
) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["rolling_mean"] = df[price_col].rolling(window).mean()
    df["deviation_pct"] = (df[price_col] / df["rolling_mean"] - 1) * 100
    return df.dropna(subset=["rolling_mean"]).reset_index(drop=True)


def get_deviation_levels(
    df: pd.DataFrame,
    col: str = "deviation_pct",
    sigma_levels: Optional[Iterable[int]] = None,
) -> Dict[str, float]:
    sigma_levels = list(sigma_levels or [1, 2])
    mean = float(df[col].mean())
    std = float(df[col].std())
    levels: Dict[str, float] = {"mean": mean}
    for s in sigma_levels:
        levels[f"+{s}σ"] = mean + s * std
        levels[f"-{s}σ"] = mean - s * std
    return levels


def get_quantile_thresholds(series: pd.Series, window: int = 504) -> Dict[str, float]:
    if series is None or series.empty or len(series) < 200:
        return {"p5": 0.0, "p10": 0.0, "p90": 0.0, "p95": 0.0}

    lookback = series.iloc[-window:]
    # OPTIMIZED: один батч-вызов quantile вместо 4 отдельных; метод/интерполяция те же.
    q = lookback.quantile([0.05, 0.10, 0.90, 0.95])

    return {
        "p5": round(float(q.loc[0.05]), 2),
        "p10": round(float(q.loc[0.10]), 2),
        "p90": round(float(q.loc[0.90]), 2),
        "p95": round(float(q.loc[0.95]), 2),
    }


def calculate_z_score(
    df: pd.DataFrame,
    column: str = "Large_Specs_Net",
    window: int = 104,
) -> pd.DataFrame:
    df = df.copy()
    roll_mean = df[column].rolling(window).mean()
    roll_std = df[column].rolling(window).std()
    df["Z_Score_Large"] = (df[column] - roll_mean) / roll_std
    return df.dropna(subset=["Z_Score_Large"]).reset_index(drop=True)


def calculate_cot_composite(
    comm_idx: float,
    large_inv_idx: float,
    z_score: float,
    thresholds: Dict[str, float],
) -> tuple[float, str]:
    score = 0.0
    parts: list[str] = []

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

    if z_score >= 3.0:
        score -= 1.0
        parts.append("Z ≥3.0 → Bear penalty")
    elif z_score <= -3.0:
        score += 1.0
        parts.append("Z ≤-3.0 → Bull boost")

    return round(score, 2), " | ".join(parts) if parts else "COT neutral"