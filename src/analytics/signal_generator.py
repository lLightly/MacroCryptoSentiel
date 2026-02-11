# MacroCryptoSentinel/src/analytics/signal_generator.py
# (Оставляем заглушку — добавишь логику сигналов позже)
def generate_signal(deviation_pct: float, threshold: float = 30.0):
    """
    Пример простой логики mean reversion для VIX:
    - Если сильно выше среднего (> +2σ %) → ожидать падения VIX (сигнал ЛОНГ по рынку)
    - Если сильно ниже среднего (< -2σ %) → ожидать роста VIX (сигнал ШОРТ)
    """
    if deviation_pct > threshold:
        return "СИЛЬНЫЙ ЛОНГ (VIX перекуплен)"
    elif deviation_pct < -threshold:
        return "СИЛЬНЫЙ ШОРТ (VIX перепродан)"
    return "НЕЙТРАЛЬНО"