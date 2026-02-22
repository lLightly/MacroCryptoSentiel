import pandas as pd
from src.analytics.signal_generator import score_asset
from src.config.settings import get_settings

# Включаем Compass mode, чтобы тест шел по нужной ветке
get_settings().compass_mode = True

# Симулируем: Прайс есть, а данных COT вообще нет (или они пустые)
fake_dfs = {
    "btc": pd.DataFrame({
        "date": pd.date_range("2026-01-01", "2026-02-21"), 
        "close": [50000] * 52
    }),
    "btc_cot": pd.DataFrame() # Пустой COT!
}

table, total, verdict, conf, narr = score_asset("BTC", fake_dfs)

print(f"Вердикт: {verdict}")
print(f"Общий Score: {total}")
print("Факторы:")
print(table[["Factor", "Score", "Rationale"]].to_string(index=False))

# Если баг исправлен, скрипт покажет:
# Factor: COT Composite | Score: 0.0 | Rationale: COT: No recent data (или его вообще не будет в таблице)
