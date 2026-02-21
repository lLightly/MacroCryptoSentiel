from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def _ensure_datetime_inplace(df: pd.DataFrame) -> None:
    # OPTIMIZED: быстрый путь — не гоняем pd.to_datetime повторно, если dtype уже datetime-like.
    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])


def build_features(dfs: Dict[str, pd.DataFrame], asset: str, for_signals: bool) -> pd.DataFrame:
    s = get_settings()
    sc = s.scoring
    ml_enabled = sc.ml_enabled
    asset_key = asset.lower()
    df_price = dfs.get(asset_key)
    if df_price is None or df_price.empty:
        return pd.DataFrame()

    df = df_price[["date", "close"]].copy()
    _ensure_datetime_inplace(df)

    if sc.vix_enabled or ml_enabled:
        if "vix" in dfs and dfs["vix"] is not None and not dfs["vix"].empty:
            vix = dfs["vix"][["date", "deviation_pct"]].copy()
            _ensure_datetime_inplace(vix)
            df = df.merge(vix, on="date", how="left").rename(columns={"deviation_pct": "vix_dev"})

    cot_key = f"{asset_key}_cot"
    if sc.cot_enabled or ml_enabled:
        if cot_key in dfs and dfs[cot_key] is not None and not dfs[cot_key].empty:
            cot = dfs[cot_key][
                ["date", "COT_Index_Comm_26w", "COT_Index_Large_Inverted_26w", "Z_Score_Large"]
            ].copy()
            _ensure_datetime_inplace(cot)
            df = df.merge(cot, on="date", how="left").rename(
                columns={
                    "COT_Index_Comm_26w": "cot_comm",
                    "COT_Index_Large_Inverted_26w": "cot_large_inv",
                    "Z_Score_Large": "z_large",
                }
            )

    if sc.liquidity_enabled or ml_enabled:
        if "dxy" in dfs and dfs["dxy"] is not None and not dfs["dxy"].empty:
            dxy = dfs["dxy"][["date", "close"]].copy()
            _ensure_datetime_inplace(dxy)
            dxy["dxy_30d"] = (dxy["close"] / dxy["close"].shift(30) - 1) * 100
            df = df.merge(dxy[["date", "dxy_30d"]], on="date", how="left")

        if "us10y" in dfs and dfs["us10y"] is not None and not dfs["us10y"].empty:
            us10y = dfs["us10y"][["date", "close"]].copy()
            _ensure_datetime_inplace(us10y)
            us10y["us10y_30d"] = (us10y["close"] / us10y["close"].shift(30) - 1) * 100
            df = df.merge(us10y[["date", "us10y_30d"]], on="date", how="left")

    if sc.correlation_enabled or ml_enabled:
        if "spx" in dfs and dfs["spx"] is not None and not dfs["spx"].empty:
            spx = dfs["spx"][["date", "close"]].copy()
            _ensure_datetime_inplace(spx)
            merged = df[["date", "close"]].merge(spx, on="date", suffixes=("_asset", "_spx"), how="left")
            merged["spx_corr"] = merged["close_asset"].rolling(60, min_periods=30).corr(merged["close_spx"])
            df = df.merge(merged[["date", "spx_corr"]], on="date", how="left")

    if sc.momentum_enabled or ml_enabled:
        df["mom_30d"] = (df["close"] / df["close"].shift(30) - 1) * 100

    if sc.trend_filter_enabled or ml_enabled:
        df["above_200ma"] = (df["close"] > df["close"].rolling(200, min_periods=100).mean()).astype(int)

    if not for_signals:
        horizon = int(s.ml.target_horizon_days)
        df["target"] = (df["close"].shift(-horizon) / df["close"] - 1) * 100

    possible_cols = [
        "vix_dev",
        "cot_comm",
        "cot_large_inv",
        "z_large",
        "mom_30d",
        "dxy_30d",
        "us10y_30d",
        "spx_corr",
        "above_200ma",
    ]
    feature_cols = [c for c in possible_cols if c in df.columns]
    if not for_signals:
        feature_cols.append("target")

    df = df.sort_values("date").reset_index(drop=True)
    df = df.ffill().fillna(0)
    df = df.dropna(subset=feature_cols, how="all")

    return df.reset_index(drop=True)