from __future__ import annotations

import logging
from typing import Dict, Tuple

import pandas as pd

from src.analytics.features import build_features
from src.analytics.ml import FEATURES, train_ml_model
from src.analytics.scoring import (
    apply_trend_filter,
    corr_penalty,
    liquidity_score,
    momentum_score,
    verdict_from_total,
    vix_score,
)
from src.analytics.statistics import calculate_cot_composite, get_quantile_thresholds
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def score_asset(asset: str, dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, float, str, float]:
    s = get_settings()
    sc = s.scoring

    # OPTIMIZED: строим фичи 1 раз (с target), затем используем и для сигналов, и для обучения.
    df_all = build_features(dfs, asset, for_signals=False)
    if df_all.empty or len(df_all) < s.signals.min_feature_rows:
        return pd.DataFrame(), 0.0, "No data", 0.0

    df_features = df_all.drop(columns=["target"]) # OPTIMIZED: эквивалент build_features(..., for_signals=True)

    horizon = s.ml.target_horizon_days
    train_df = df_all
    if len(train_df) > horizon:
        train_df = train_df.iloc[:-horizon]

    latest = df_features.iloc[-1]

    rows = []

    ml_score = 0.0
    if sc.ml_enabled:
        model = train_ml_model(train_df)
        latest_row = latest.reindex(FEATURES).astype(float)
        try:
            # Оставляем DataFrame, чтобы не менять поведение sklearn (и не получить предупреждений о feature names)
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
        vix_series = dfs.get("vix", pd.DataFrame()).get("deviation_pct", pd.Series(dtype=float))
        vix_thresh = get_quantile_thresholds(vix_series)
        v_score, v_text = vix_score(float(latest.get("vix_dev", 0.0)), vix_thresh)
        rows.append(("VIX deviation", v_score, v_text))

    if sc.cot_enabled:
        cot_thresh = get_quantile_thresholds(df_features["cot_comm"])
        cot_score, cot_text = calculate_cot_composite(
            float(latest.get("cot_comm", 0.0)),
            float(latest.get("cot_large_inv", 0.0)),
            float(latest.get("z_large", 0.0)),
            cot_thresh,
        )
        rows.append(("COT Composite", cot_score, cot_text))

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


def generate_conclusion(dfs: Dict[str, pd.DataFrame]):
    per_asset = {}
    for asset in ["BTC", "ETH"]:
        try:
            per_asset[asset] = score_asset(asset, dfs)
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


def generate_signals(
    dfs_full: Dict[str, pd.DataFrame],
    asset: str = "BTC",
) -> pd.DataFrame:
    s = get_settings()
    sig = s.signals # OPTIMIZED: локальная ссылка, меньше атрибутных обращений
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

    # OPTIMIZED: заранее готовим “план нарезки” для каждого df:
    # - если date монотонно возрастает => searchsorted + iloc (O(logN))
    # - иначе fallback на старую маску (сохранение поведения для edge-case несортированных данных)
    slice_plan = {}
    for k, v in dfs_full.items():
        if v is None or v.empty:
            slice_plan[k] = (None, None, False)
            continue

        # ВАЖНО: не добавляем защиту на отсутствие "date", чтобы не менять исключения (KeyError остаётся возможным как раньше).
        date_col = v["date"]
        fast = pd.api.types.is_datetime64_any_dtype(date_col) and getattr(date_col, "is_monotonic_increasing", False)
        date_values = date_col.to_numpy() if fast else None
        slice_plan[k] = (v, date_values, fast)

    # OPTIMIZED: переиспользуем один dict под sliced, чтобы снизить аллокации в цикле
    sliced: Dict[str, pd.DataFrame] = {}

    for i in range(start_i, len(df_price) - step, step):
        current_date = df_price.loc[i, "date"]

        cur64 = current_date.to_datetime64()

        for k, (v, date_values, fast) in slice_plan.items():
            if v is None:
                sliced[k] = pd.DataFrame()
                continue

            if fast:
                # OPTIMIZED: searchsorted + iloc вместо boolean mask (быстрее на порядок на длинных рядах)
                pos = date_values.searchsorted(cur64, side="right")
                sliced[k] = v.iloc[:pos]
            else:
                # OPTIMIZED: fallback = исходная семантика (сохраняем порядок строк при несортированных df)
                sliced[k] = v[v["date"] <= current_date]

        table, total, verdict, conf = score_asset(asset, sliced)

        vix_df = sliced.get("vix", pd.DataFrame())
        latest_vix = float(vix_df["deviation_pct"].iloc[-1]) if not vix_df.empty and "deviation_pct" in vix_df.columns else 0.0

        # OPTIMIZED: inline dynamic_min_score (та же формула и порядок операций)
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
            # OPTIMIZED: без set_index/to_dict (меньше аллокаций), порядок ключей сохраняется как в таблице.
            row.update(dict(zip(table["Factor"].tolist(), table["Score"].tolist())))
        results.append(row)

    if not results:
        return pd.DataFrame(columns=["date", "total_score", "verdict", "signal", "confidence"])

    df_signals = pd.DataFrame(results).sort_values("date").reset_index(drop=True)
    df_signals["date"] = pd.to_datetime(df_signals["date"]).dt.normalize()
    return df_signals