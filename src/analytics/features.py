# src/analytics/features.py (modified)
from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def _ensure_datetime_inplace(df: pd.DataFrame) -> None:
    if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])


def build_features(dfs: Dict[str, pd.DataFrame], asset: str, for_signals: bool) -> pd.DataFrame:
    logger.debug(f"Building features for {asset}, for_signals={for_signals}")
    logger.debug(f"Input dfs keys: {list(dfs.keys())}")

    s = get_settings()
    sc = s.scoring
    ml_enabled = sc.ml_enabled
    asset_key = asset.lower()
    df_price = dfs.get(asset_key)
    if df_price is None or df_price.empty:
        logger.warning(f"No price data for {asset}")
        return pd.DataFrame()

    logger.debug(f"Price df shape: {df_price.shape}")
    logger.debug(f"Price df head: {df_price.head().to_dict()}")

    df = df_price[["date", "close"]].copy()
    _ensure_datetime_inplace(df)
    df = df.sort_values("date").reset_index(drop=True)

    if sc.vix_enabled or ml_enabled:
        if "vix" in dfs and dfs["vix"] is not None and not dfs["vix"].empty:
            vix = dfs["vix"][["date", "deviation_pct"]].copy()
            _ensure_datetime_inplace(vix)
            vix = vix.sort_values("date").reset_index(drop=True)
            logger.debug(f"VIX df shape before merge: {vix.shape}")
            # FIX: Changed direction to "nearest" for VIX merge to handle potential date mismatches
            df = pd.merge_asof(df, vix, on="date", direction="nearest").rename(columns={"deviation_pct": "vix_dev"})
            logger.debug(f"After VIX merge, df shape: {df.shape}")
            logger.debug(f"Latest vix_dev: {df['vix_dev'].iloc[-1] if 'vix_dev' in df else 'None'}")

    cot_key = f"{asset_key}_cot"
    if sc.cot_enabled or ml_enabled:
        if cot_key in dfs and dfs[cot_key] is not None and not dfs[cot_key].empty:
            cot = dfs[cot_key][
                ["date", "COT_Index_Comm_26w", "COT_Index_Large_Inverted_26w", "Z_Score_Comm"] # ← Z_Comm
            ].copy()
            _ensure_datetime_inplace(cot)
            cot = cot.sort_values("date").reset_index(drop=True)
            logger.debug(f"COT df shape before merge: {cot.shape}")
            df = pd.merge_asof(df, cot, on="date", direction="backward").rename(
                columns={
                    "COT_Index_Comm_26w": "cot_comm",
                    "COT_Index_Large_Inverted_26w": "cot_large_inv",
                    "Z_Score_Comm": "z_comm", # ← z_comm
                }
            )
            logger.debug(f"After COT merge, df shape: {df.shape}")
            logger.debug(f"Latest cot_comm: {df['cot_comm'].iloc[-1] if 'cot_comm' in df else 'None'}")

    if sc.liquidity_enabled or ml_enabled:
        if "dxy" in dfs and dfs["dxy"] is not None and not dfs["dxy"].empty:
            dxy = dfs["dxy"][["date", "close"]].copy()
            _ensure_datetime_inplace(dxy)
            dxy = dxy.sort_values("date").reset_index(drop=True)
            dxy["dxy_30d"] = (dxy["close"] / dxy["close"].shift(30) - 1) * 100
            logger.debug(f"DXY df shape before merge: {dxy.shape}")
            df = pd.merge_asof(df, dxy[["date", "dxy_30d"]], on="date", direction="nearest")
            logger.debug(f"After DXY merge, df shape: {df.shape}")

        if "us10y" in dfs and dfs["us10y"] is not None and not dfs["us10y"].empty:
            us10y = dfs["us10y"][["date", "close"]].copy()
            _ensure_datetime_inplace(us10y)
            us10y = us10y.sort_values("date").reset_index(drop=True)
            us10y["us10y_30d"] = (us10y["close"] / us10y["close"].shift(30) - 1) * 100
            logger.debug(f"US10Y df shape before merge: {us10y.shape}")
            df = pd.merge_asof(df, us10y[["date", "us10y_30d"]], on="date", direction="nearest")
            logger.debug(f"After US10Y merge, df shape: {df.shape}")

    if sc.correlation_enabled or ml_enabled:
        if "spx" in dfs and dfs["spx"] is not None and not dfs["spx"].empty:
            spx = dfs["spx"][["date", "close"]].copy()
            _ensure_datetime_inplace(spx)
            spx = spx.sort_values("date").reset_index(drop=True)
            merged = pd.merge_asof(
                df[["date", "close"]].rename(columns={"close": "close_asset"}),
                spx.rename(columns={"close": "close_spx"}),
                on="date",
                direction="nearest"
            )
            merged["spx_corr"] = merged["close_asset"].rolling(60, min_periods=30).corr(merged["close_spx"])
            df = pd.merge_asof(df, merged[["date", "spx_corr"]], on="date", direction="nearest")
            logger.debug(f"After SPX corr, df shape: {df.shape}")

    if sc.momentum_enabled or ml_enabled:
        df["mom_30d"] = (df["close"] / df["close"].shift(30) - 1) * 100
        logger.debug(f"mom_30d calculated")

    if sc.trend_filter_enabled or ml_enabled:
        df["above_200ma"] = (df["close"] > df["close"].rolling(200, min_periods=100).mean()).astype(int)
        logger.debug(f"above_200ma calculated")

    if not for_signals:
        horizon = int(s.ml.target_horizon_days)
        df["target"] = (df["close"].shift(-horizon) / df["close"] - 1) * 100
        logger.debug(f"Target calculated for horizon {horizon}")

    possible_cols = [
        "vix_dev",
        "cot_comm",
        "cot_large_inv",
        "z_comm", # ← обновлено
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
    df = df.ffill()
    
    # Для ML заполняем NaN нулями, для сигналов оставляем NaN
    if not for_signals:
        df = df.fillna(0)
    
    df = df.dropna(subset=feature_cols, how="all")
    
    return df.reset_index(drop=True)