# src/analytics/scoring.py
from __future__ import annotations

from typing import Dict, Tuple

from src.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('app.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def vix_score(dev_pct: float, levels: Dict[str, float]) -> Tuple[float, str]:
    """VIX scoring по mean-reversion + твоя логика:
    +3σ = экстремальное дно → ультра-закупка в спот
    +2σ = сильное дно → закупка
    -3σ / -2σ = комплаенс на максимуме → сильная продажа"""
    s = get_settings().scoring

    logger.debug(f"VIX dev_pct: {dev_pct}, levels: {levels}")

    if dev_pct >= levels.get("+3σ", 999):
        score = 1000  # чтобы гарантированно сработал Bullish
        text = "VIX ≥ +3σ → ЭКСТРЕМАЛЬНОЕ ДНО! Максимальная закупка в спот. Ожидаем мощнейшего отскока BTC (импульс VIX → симметричный рост актива)"
    elif dev_pct >= levels.get("+2σ", 999):
        score = s.vix_strong_risk_on_score
        text = "VIX ≥ +2σ → Актив на дне! Закупаемся в спот (Buy the fear). При падении VIX BTC вырастет примерно в той же пропорции"
    elif dev_pct >= levels.get("+1σ", 999):
        score = s.vix_risk_on_score
        text = "VIX ≥ +1σ → Страх нарастает → умеренная покупка спота"
    elif dev_pct <= levels.get("-3σ", -999):
        score = -1000  # чтобы гарантированно сработал Bearish
        text = "VIX ≤ -3σ → Сверхкомплаенс → максимальная продажа / выход в кеш"
    elif dev_pct <= levels.get("-2σ", -999):
        score = s.vix_strong_risk_off_score
        text = "VIX ≤ -2σ → Комплаенс на максимуме → сильная продажа / не держать"
    elif dev_pct <= levels.get("-1σ", -999):
        score = s.vix_risk_off_score
        text = "VIX ≤ -1σ → Комплаенс → умеренная продажа"
    else:
        score = 0.0
        text = "VIX neutral (±1σ) — ждём движения"

    logger.debug(f"VIX score: {score}, text: {text}")
    return score, text


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
    score = 0.0
    parts = []

    if dxy_30d >= s.liquidity_dxy_strong_pct:
        score -= s.liquidity_score_each
        parts.append("DXY strong")
    elif dxy_30d <= -s.liquidity_dxy_strong_pct:
        score += s.liquidity_score_each
        parts.append("DXY weak")

    if us10y_30d >= s.liquidity_us10y_spike_pct:
        score -= s.liquidity_score_each
        parts.append("10Y spike")
    elif us10y_30d <= -s.liquidity_us10y_spike_pct:
        score += s.liquidity_score_each
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