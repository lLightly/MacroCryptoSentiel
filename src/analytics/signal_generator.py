# signal_generator.py (без изменений)
from typing import Dict

def generate_vix_signal(deviation_pct: float, levels: Dict[str, float]) -> str:
    if deviation_pct > levels["+2σ"]:
        return "СИЛЬНЫЙ ЛОНГ (VIX сильно перекуплен → ожидать падения волатильности)"
    elif deviation_pct > levels["+1σ"]:
        return "Умеренный ЛОНГ"
    elif deviation_pct < levels["-2σ"]:
        return "СИЛЬНЫЙ ШОРТ (VIX сильно перепродан → ожидать роста волатильности)"
    elif deviation_pct < levels["-1σ"]:
        return "Умеренный ШОРТ"
    else:
        return "НЕЙТРАЛЬНО"


def generate_cot_large_signal(inverted_large_index: float) -> str:
    if inverted_large_index > 80:
        return "ЭКСТРЕМАЛЬНО БЫЧИЙ (крупные спекулянты экстремально короткие)"
    elif inverted_large_index > 60:
        return "Бычий"
    elif inverted_large_index < 20:
        return "ЭКСТРЕМАЛЬНО МЕДВЕЖИЙ (крупные спекулянты экстремально длинные)"
    elif inverted_large_index < 40:
        return "Медвежий"
    else:
        return "Нейтрально"


def generate_cot_comm_signal(comm_index: float) -> str:
    if comm_index > 80:
        return "ЭКСТРЕМАЛЬНО МЕДВЕЖИЙ (коммерческие экстремально длинные)"
    elif comm_index > 60:
        return "Медвежий"
    elif comm_index < 20:
        return "ЭКСТРЕМАЛЬНО БЫЧИЙ (коммерческие экстремально короткие)"
    elif comm_index < 40:
        return "Бычий"
    else:
        return "Нейтрально"