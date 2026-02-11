# MacroCryptoSentinel/main.py
import os
from src.data_fetchers.finance_api import fetch_all_market_data
from src.analytics.statistics import add_vix_deviation_indicators
from src.utils.helpers import save_csv

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

def main():
    print("Скачиваем рыночные данные (VIX, BTC)...")
    data = fetch_all_market_data()

    save_csv(data["vix"], "data/raw/vix.csv")
    save_csv(data["btc"], "data/raw/btcusdt.csv")
    print("Сырые данные сохранены в data/raw/")

    # Обработка VIX с новым индикатором отклонения
    vix_processed = add_vix_deviation_indicators(data["vix"], window=52)

    save_csv(vix_processed, "data/processed/vix_processed.csv")
    print("Обработанные данные VIX сохранены в data/processed/vix_processed.csv")


if __name__ == "__main__":
    main()