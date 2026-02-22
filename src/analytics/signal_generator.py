# src/analytics/signal_generator.py
from __future__ import annotations

import logging
from typing import Dict, Tuple

import pandas as pd
import numpy as np

from src.analytics.statistics import get_deviation_levels
from src.analytics.features import build_features
from src.analytics.scoring import vix_score
from src.analytics.statistics import calculate_cot_composite, get_quantile_thresholds
from src.config.settings import get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


# -------------------------
# Global Compass (Macro+COT)
# -------------------------

def _safe_float(v, default: float = np.nan) -> float:
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _compass_verdict(total: float) -> str:
    # Coarse, interpretive regime call.
    thr = float(get_settings().scoring.verdict_buy)
    if total >= thr:
        return "Bullish Trend"
    if total <= -thr:
        return "Bearish Trend"
    return "Neutral"


def _compass_confidence(df_feat: pd.DataFrame, required_cols: list[str], min_rows: int) -> float:
    if df_feat is None or df_feat.empty or not required_cols:
        return 0.0

    latest = df_feat.iloc[-1]
    latest_ok = sum(pd.notna(latest.get(c)) for c in required_cols) / max(1, len(required_cols))

    hist_ok_rows = df_feat.dropna(subset=required_cols, how="any")
    hist_ok = min(1.0, len(hist_ok_rows) / max(1, min_rows))

    conf = 0.5 * latest_ok + 0.5 * hist_ok
    return float(max(0.0, min(1.0, conf)))


# src/analytics/signal_generator.py (modified function _score_asset_compass)
def _score_asset_compass(asset: str, dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, float, str, float, str]:
    """
    Returns:
    (df_table, total, verdict, confidence, narrative)
    """
    logger.debug(f"Scoring asset {asset}")
    logger.debug(f"dfs keys in score: {list(dfs.keys())}")

    s = get_settings()
    sc = s.scoring

    df_feat = build_features(dfs, asset, for_signals=True)
    if df_feat.empty or len(df_feat) < s.signals.min_feature_rows:
        logger.warning(f"No sufficient features for {asset}")
        empty_table = pd.DataFrame([["No data", 0.0, "Insufficient price or feature data"]], 
                                   columns=["Factor", "Score", "Rationale"])
        return empty_table, 0.0, "No data", 0.0, ""

    logger.debug(f"Features df in score: {df_feat.shape}")

    latest = df_feat.iloc[-1]
    logger.debug(f"Latest features: {latest.to_dict()}")

    rows: list[tuple[str, float, str]] = []

    # ==================== VIX ====================
    if sc.vix_enabled:
        vix_df = dfs.get("vix")
        if vix_df is None or vix_df.empty:
            rows.append(("VIX Risk Regime", 0.0, "VIX: No data"))
        else:
            dev_levels = get_deviation_levels(vix_df, sigma_levels=s.ui.sigma_levels)
            if dev_levels is None:
                rows.append(("VIX Risk Regime", 0.0, "VIX: Not enough data for levels"))
            else:
                dev_pct = _safe_float(latest.get("vix_dev"))
                if pd.isna(dev_pct):
                    rows.append(("VIX Risk Regime", 0.0, "VIX: No recent data"))
                else:
                    v_score, v_text = vix_score(dev_pct, dev_levels)
                    rows.append(("VIX Risk Regime", float(v_score), v_text))

    # ==================== COT ====================
    if sc.cot_enabled:
        cot_key = f"{asset.lower()}_cot"
        cot_df = dfs.get(cot_key)
        if cot_df is None or cot_df.empty:
            rows.append(("COT Composite", 0.0, "COT: No data"))
        else:
            cot_thresh = get_quantile_thresholds(df_feat.get("cot_comm", pd.Series(dtype=float)))
            if cot_thresh is None:
                rows.append(("COT Composite", 0.0, "COT: Not enough data for quantiles"))
            else:
                cot_comm_val = _safe_float(latest.get("cot_comm"))
                if pd.isna(cot_comm_val):
                    rows.append(("COT Composite", 0.0, "COT: No recent data"))
                else:
                    cot_score, cot_text = calculate_cot_composite(
                        cot_comm_val,
                        _safe_float(latest.get("cot_large_inv"), default=50.0),
                        _safe_float(latest.get("z_comm"), default=0.0),
                        cot_thresh,
                    )
                    rows.append(("COT Composite", float(cot_score), cot_text))

    # ==================== ГАРАНТИЯ (никогда не пустая таблица) ====================
    if not rows:
        rows.append(("No Factors", 0.0, "No enabled factors or data available"))

    df_table = pd.DataFrame(rows, columns=["Factor", "Score", "Rationale"])

    total = float(df_table["Score"].sum()) if not df_table.empty else 0.0
    verdict = _compass_verdict(total)

    required = [c for c in ["vix_dev", "cot_comm", "cot_large_inv", "z_comm"] if c in df_feat.columns]
    confidence = round(_compass_confidence(df_feat, required, min_rows=s.signals.min_feature_rows), 2)

    # FIX: Только по confidence, без checks на rationale — partial data дает verdict from available, с lowered conf
    if confidence <= 0.01:
        verdict = "No data"

    # Narrative
    narrative_parts: list[str] = []
    for _, r in df_table.iterrows():
        narrative_parts.append(f"- **{r['Factor']}**: {r['Rationale']} (score {float(r['Score']):+.2f})")
    narrative = "\n".join(narrative_parts) if narrative_parts else ""

    return df_table, round(total, 2), verdict, confidence, narrative


def _generate_conclusion_compass(dfs: Dict[str, pd.DataFrame]):
    logger.debug("Generating compass conclusion")
    per_asset: dict[str, tuple[pd.DataFrame, float, str, float, str]] = {}
    valid_totals: list[float] = []
    narratives: list[str] = []

    for asset in ["BTC", "ETH"]:
        try:
            df_table, total, verdict, conf, narrative = _score_asset_compass(asset, dfs)
            per_asset[asset] = (df_table, total, verdict, conf, narrative)
            if verdict != "No data":
                valid_totals.append(float(total))
            if narrative:
                narratives.append(f"### {asset}\n{narrative}")
        except Exception as e:
            logger.exception("Compass score_asset failed for %s: %s", asset, e)
            per_asset[asset] = (pd.DataFrame(), 0.0, "Neutral", 0.0, "")

    combined_score = sum(valid_totals) / len(valid_totals) if valid_totals else 0.0
    combined_score = round(float(combined_score), 2)
    combined_verdict = _compass_verdict(combined_score)
    logger.debug(f"Combined score: {combined_score}, verdict: {combined_verdict}")

    combined_narrative = "\n\n".join(narratives)
    if combined_narrative:
        combined_narrative = f"## Market narrative\n\n{combined_narrative}"
    logger.debug(f"Combined narrative: {combined_narrative}")

    return per_asset, combined_score, combined_verdict, combined_narrative


def _generate_signals_compass(dfs_full: Dict[str, pd.DataFrame], asset: str = "BTC") -> pd.DataFrame:
    logger.debug(f"Generating compass signals for {asset}")
    s = get_settings()
    sig = s.signals
    asset_key = asset.lower()
    df_price = dfs_full.get(asset_key)
    if df_price is None or len(df_price) < sig.min_price_rows:
        logger.warning(f"No price data for signals {asset}")
        return pd.DataFrame(columns=["date", "total_score", "verdict", "position", "confidence"])

    df_price = df_price.copy()
    df_price["date"] = pd.to_datetime(df_price["date"]).dt.normalize()
    df_price = df_price.sort_values("date").reset_index(drop=True)
    logger.debug(f"Price for signals shape: {df_price.shape}")

    # FIX: В Compass mode игнорируем start_fraction, чтобы генерировать сигналы с начала (min_start_bars ~1)
    if s.compass_mode:
        start_i = sig.min_start_bars
    else:
        start_i = max(sig.min_start_bars, int(len(df_price) * sig.start_fraction))
    
    step = int(sig.step_days)
    results = []

    # slice plan (fast) — остальное без изменений
    slice_plan = {}
    for k, v in dfs_full.items():
        if v is None or v.empty:
            slice_plan[k] = (None, None, False)
            continue
        date_col = v["date"]
        fast = pd.api.types.is_datetime64_any_dtype(date_col) and getattr(date_col, "is_monotonic_increasing", False)
        date_values = date_col.to_numpy() if fast else None
        slice_plan[k] = (v, date_values, fast)

    sliced: Dict[str, pd.DataFrame] = {}

    for i in range(start_i, len(df_price), step):
        current_date = df_price.loc[i, "date"]
        logger.debug(f"Processing date {current_date}")
        cur64 = current_date.to_datetime64()

        for k, (v, date_values, fast) in slice_plan.items():
            if v is None:
                sliced[k] = pd.DataFrame()
                continue
            if fast:
                pos = date_values.searchsorted(cur64, side="right")
                sliced[k] = v.iloc[:pos]
            else:
                sliced[k] = v[v["date"] <= current_date]
            logger.debug(f"Sliced {k} shape: {sliced[k].shape}")

        table, total, verdict, conf, _narr = _score_asset_compass(asset, sliced)

        position = 1 if verdict == "Bullish Trend" else 0
        row = {
            "date": current_date,
            "total_score": total,
            "verdict": verdict,
            "position": position,
            "confidence": conf,
        }
        if not table.empty:
            row.update(dict(zip(table["Factor"].tolist(), table["Score"].tolist())))
        results.append(row)
        logger.debug(f"Signal row: {row}")

    if not results:
        logger.warning("No signals generated")
        return pd.DataFrame(columns=["date", "total_score", "verdict", "position", "confidence"])

    df_signals = pd.DataFrame(results).sort_values("date").reset_index(drop=True)
    df_signals["date"] = pd.to_datetime(df_signals["date"]).dt.normalize()
    logger.debug(f"Signals df: {df_signals.to_dict()}")

    return df_signals


# -----------------------------
# Legacy hybrid stack (Scalpel)
# -----------------------------
def _score_asset_legacy(asset: str, dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, float, str, float]:
    """
    Original implementation kept for backward compatibility.
    Imports are local to keep Compass mode lightweight.
    """
    from src.analytics.ml import FEATURES, train_ml_model
    from src.analytics.scoring import (
        apply_trend_filter,
        corr_penalty,
        liquidity_score,
        momentum_score,
        verdict_from_total,
    )

    s = get_settings()
    sc = s.scoring

    df_all = build_features(dfs, asset, for_signals=False)
    if df_all.empty or len(df_all) < s.signals.min_feature_rows:
        return pd.DataFrame(), 0.0, "No data", 0.0

    df_features = df_all.drop(columns=["target"])

    horizon = s.ml.target_horizon_days
    train_df = df_all
    if len(train_df) > horizon:
        train_df = train_df.iloc[:-horizon]

    latest = df_features.iloc[-1]
    rows = []

    if sc.ml_enabled:
        model = train_ml_model(train_df)
        latest_row = latest.reindex(FEATURES).astype(float)
        try:
            predicted_return = float(model.predict(pd.DataFrame([latest_row]))[0])
        except Exception:
            predicted_return = 0.0
        ml_score = predicted_return / s.ml.pred_to_score_divisor
        trend_text = "No trend filter"
        if s.scoring.trend_filter_enabled:
            ml_score, trend_text = apply_trend_filter(ml_score, int(latest.get("above_200ma", 1)))
        if predicted_return != 0:
            rows.append(("ML Predicted Return", round(ml_score, 2), f"{predicted_return:.2f}% | {trend_text}"))

    if sc.vix_enabled:
        vix_df = dfs.get("vix")
        if vix_df is not None and not vix_df.empty and "deviation_pct" in vix_df.columns:
            s = get_settings()
            vix_levels = get_deviation_levels(vix_df, sigma_levels=s.ui.sigma_levels)
            v_score, v_text = vix_score(float(latest.get("vix_dev", 0.0)), vix_levels)
            rows.append(("VIX deviation", v_score, v_text))

    # COT composite
    if sc.cot_enabled and "cot_comm" in df_features.columns:
        cot_comm_val = _safe_float(latest.get("cot_comm"))
        
        if pd.notna(cot_comm_val):
            cot_thresh = get_quantile_thresholds(df_features["cot_comm"])
            if cot_thresh is not None:
                cot_score, cot_text = calculate_cot_composite(
                    cot_comm_val,
                    _safe_float(latest.get("cot_large_inv"), default=50.0),
                    _safe_float(latest.get("z_comm"), default=0.0),
                    cot_thresh,
                )
                rows.append(("COT Composite", float(cot_score), cot_text))
            else:
                rows.append(("COT Composite", 0.0, "COT: Not enough data for quantiles"))
        else:
            rows.append(("COT Composite", 0.0, "COT: No recent data"))


    if sc.momentum_enabled:
        m_score, m_text = momentum_score(float(latest.get("mom_30d", 0.0)))
        rows.append((f"{asset} 30d momentum", m_score, m_text))

    if sc.liquidity_enabled:
        l_score, l_text = liquidity_score(float(latest.get("dxy_30d", 0.0)), float(latest.get("us10y_30d", 0.0)))
        rows.append(("Liquidity", l_score, l_text))

    if sc.correlation_enabled:
        c_score, c_text = corr_penalty(float(latest.get("spx_corr", 0.0)))
        rows.append(("SPX corr penalty", c_score, c_text))

    df_table = pd.DataFrame(rows, columns=["Factor", "Score", "Rationale"])
    total = float(df_table["Score"].sum())
    verdict = verdict_from_total(total)
    confidence = min(1.0, abs(total) / 5.0)

    return df_table, round(total, 2), verdict, round(confidence, 2)


def _generate_conclusion_legacy(dfs: Dict[str, pd.DataFrame]):
    per_asset = {}
    for asset in ["BTC", "ETH"]:
        try:
            per_asset[asset] = _score_asset_legacy(asset, dfs)
        except Exception as e:
            logger.exception("score_asset failed for %s: %s", asset, e)
            per_asset[asset] = (pd.DataFrame(), 0.0, "Neutral", 0.0)

    combined = (per_asset["BTC"][1] + per_asset["ETH"][1]) / 2
    combined_verdict = (
        "🚀 Сильный лонг"
        if combined >= 4.0
        else "📈 Лонг"
        if combined >= 2.2
        else "⚖️ Нейтрально"
        if abs(combined) < 1.8
        else "🔻 Шорт"
        if combined > -4.0
        else "🛑 Сильный шорт"
    )
    return per_asset, round(combined, 2), combined_verdict


def _generate_signals_legacy(dfs_full: Dict[str, pd.DataFrame], asset: str = "BTC") -> pd.DataFrame:
    s = get_settings()
    sig = s.signals
    asset_key = asset.lower()
    df_price = dfs_full.get(asset_key)
    if df_price is None or len(df_price) < sig.min_price_rows:
        return pd.DataFrame(columns=["date", "total_score", "verdict", "signal", "confidence"])

    df_price = df_price.copy()
    df_price["date"] = pd.to_datetime(df_price["date"]).dt.normalize()
    df_price = df_price.sort_values("date").reset_index(drop=True)

    start_i = max(sig.min_start_bars, int(len(df_price) * sig.start_fraction))
    step = int(sig.step_days)
    results = []

    slice_plan = {}
    for k, v in dfs_full.items():
        if v is None or v.empty:
            slice_plan[k] = (None, None, False)
            continue
        date_col = v["date"]
        fast = pd.api.types.is_datetime64_any_dtype(date_col) and getattr(date_col, "is_monotonic_increasing", False)
        date_values = date_col.to_numpy() if fast else None
        slice_plan[k] = (v, date_values, fast)

    sliced: Dict[str, pd.DataFrame] = {}

    for i in range(start_i, len(df_price) - step, step):
        current_date = df_price.loc[i, "date"]
        cur64 = current_date.to_datetime64()

        for k, (v, date_values, fast) in slice_plan.items():
            if v is None:
                sliced[k] = pd.DataFrame()
                continue
            if fast:
                pos = date_values.searchsorted(cur64, side="right")
                sliced[k] = v.iloc[:pos]
            else:
                sliced[k] = v[v["date"] <= current_date]

        table, total, verdict, conf = _score_asset_legacy(asset, sliced)

        vix_df = sliced.get("vix", pd.DataFrame())
        latest_vix = float(vix_df["deviation_pct"].iloc[-1]) if not vix_df.empty and "deviation_pct" in vix_df.columns else 0.0
        dyn_thr = sig.dyn_min_score_base + sig.dyn_min_score_vix_scale * (latest_vix / sig.dyn_min_score_vix_divisor)
        signal_flag = 1 if total >= dyn_thr else 0

        row = {
            "date": current_date,
            "total_score": total,
            "verdict": verdict,
            "signal": signal_flag,
            "confidence": conf,
            "dyn_min_score": round(dyn_thr, 3),
        }
        if not table.empty:
            row.update(dict(zip(table["Factor"].tolist(), table["Score"].tolist())))
        results.append(row)

    if not results:
        return pd.DataFrame(columns=["date", "total_score", "verdict", "signal", "confidence"])

    df_signals = pd.DataFrame(results).sort_values("date").reset_index(drop=True)
    df_signals["date"] = pd.to_datetime(df_signals["date"]).dt.normalize()
    return df_signals


# -----------------
# Public API facade
# -----------------
def score_asset(asset: str, dfs: Dict[str, pd.DataFrame]):
    s = get_settings()
    if s.compass_mode:
        return _score_asset_compass(asset, dfs)
    return _score_asset_legacy(asset, dfs)


def generate_conclusion(dfs: Dict[str, pd.DataFrame]):
    logger.debug("Starting generate_conclusion")
    s = get_settings()
    if s.compass_mode:
        return _generate_conclusion_compass(dfs)
    return _generate_conclusion_legacy(dfs)


def generate_signals(dfs_full: Dict[str, pd.DataFrame], asset: str = "BTC") -> pd.DataFrame:
    logger.debug(f"Starting generate_signals for {asset}")
    s = get_settings()
    if s.compass_mode:
        return _generate_signals_compass(dfs_full, asset=asset)
    return _generate_signals_legacy(dfs_full, asset=asset)