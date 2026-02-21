from __future__ import annotations

from typing import Dict, Tuple

from src.config.settings import get_settings


def vix_score(dev_pct: float, thresh: Dict[str, float]) -> Tuple[float, str]:
    s = get_settings().scoring
    if dev_pct >= thresh.get("p95", 999):
        return s.vix_strong_risk_off_score, "VIX ≥95p"
    if dev_pct >= thresh.get("p90", 999):
        return s.vix_risk_off_score, "VIX ≥90p"
    if dev_pct <= thresh.get("p5", -999):
        return s.vix_strong_risk_on_score, "VIX ≤5p"
    if dev_pct <= thresh.get("p10", -999):
        return s.vix_risk_on_score, "VIX ≤10p"
    return 0.0, "VIX neutral"


def momentum_score(pct_30d: float) -> Tuple[float, str]:
    s = get_settings().scoring
    thr = s.momentum_strong_move_pct
    score = s.momentum_score
    if pct_30d >= thr:
        return +score, f"Momentum +{pct_30d:.1f}%"
    if pct_30d <= -thr:
        return -score, f"Momentum {pct_30d:.1f}%"
    return 0.0, "Momentum neutral"


def liquidity_score(dxy_30d: float, us10y_30d: float) -> Tuple[float, str]:
    s = get_settings().scoring
    score_each = s.liquidity_score_each
    score = 0.0
    parts = []

    if dxy_30d >= s.liquidity_dxy_strong_pct:
        score -= score_each
        parts.append("DXY strong")
    elif dxy_30d <= -s.liquidity_dxy_strong_pct:
        score += score_each
        parts.append("DXY weak")

    if us10y_30d >= s.liquidity_us10y_spike_pct:
        score -= score_each
        parts.append("10Y spike")
    elif us10y_30d <= -s.liquidity_us10y_spike_pct:
        score += score_each
        parts.append("10Y drop")

    return score, " | ".join(parts) if parts else "Liquidity neutral"


def corr_penalty(corr_60d: float) -> Tuple[float, str]:
    s = get_settings().scoring
    if corr_60d >= s.corr_threshold:
        penalty = s.corr_slope * (corr_60d - s.corr_base)
        return penalty, f"SPX corr {corr_60d:.2f}"
    return 0.0, "Corr neutral"


def apply_trend_filter(score: float, above_200ma: int) -> Tuple[float, str]:
    s = get_settings().scoring
    if not s.trend_filter_enabled:
        return score, "Trend filter off"
    if above_200ma == 0:
        return score * s.trend_penalty_multiplier, "Below 200MA (penalty)"
    return score, "Above 200MA"


def verdict_from_total(total: float) -> str:
    s = get_settings().scoring
    if total >= s.verdict_strong_buy:
        return "🚀 Strong Buy"
    if total >= s.verdict_buy:
        return "📈 Buy"
    if abs(total) < s.verdict_neutral_band:
        return "⚖️ Neutral"
    if total > s.verdict_strong_sell:
        return "🔻 Sell"
    return "🛑 Strong Sell"


def dynamic_min_score(latest_vix_dev_pct: float) -> float:
    sig = get_settings().signals
    return sig.dyn_min_score_base + sig.dyn_min_score_vix_scale * (latest_vix_dev_pct / sig.dyn_min_score_vix_divisor)