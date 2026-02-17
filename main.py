# main.py (обновленный: добавлен Z-Score в обработку COT, новые фетчи для nasdaq, dxy, us10y)
import os
from src.data_fetchers.finance_api import fetch_vix, fetch_btc, fetch_spx, fetch_eth, fetch_nasdaq, fetch_dxy, fetch_us10y
from src.data_fetchers.cot_parser import fetch_cot_raw, preprocess
from src.analytics.indicators import build_indicators
from src.analytics.statistics import add_vix_deviation_indicators, calculate_z_score
from src.utils.helpers import save_csv

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

def main():
    # VIX
    print("Скачиваем и обрабатываем VIX...")
    vix_raw = fetch_vix()
    save_csv(vix_raw, "data/raw/vix.csv")
    vix_processed = add_vix_deviation_indicators(vix_raw, window=252)
    save_csv(vix_processed, "data/processed/vix_processed.csv")

    # BTC Price
    print("Скачиваем BTC-USD...")
    btc = fetch_btc()
    save_csv(btc, "data/processed/btc_price.csv")

    # ETH Price
    print("Скачиваем ETH-USD...")
    eth = fetch_eth()
    save_csv(eth, "data/processed/eth_price.csv")

    # S&P 500
    print("Скачиваем S&P 500...")
    spx = fetch_spx()
    save_csv(spx, "data/processed/spx_price.csv")

    # Nasdaq
    print("Скачиваем Nasdaq...")
    nasdaq = fetch_nasdaq()
    save_csv(nasdaq, "data/processed/nasdaq_price.csv")

    # DXY
    print("Скачиваем DXY...")
    dxy = fetch_dxy()
    save_csv(dxy, "data/processed/dxy_price.csv")

    # US10Y
    print("Скачиваем US10Y...")
    us10y = fetch_us10y()
    save_csv(us10y, "data/processed/us10y_price.csv")

    # COT BTC
    print("Скачиваем и обрабатываем COT данные для BTC...")
    cot_raw = fetch_cot_raw('BTC')
    if not cot_raw.empty:
        save_csv(cot_raw, "data/raw/btc_cot_raw.csv")
        cot_processed = preprocess(cot_raw)
        cot_processed = build_indicators(cot_processed)
        cot_processed = calculate_z_score(cot_processed)  # Добавлен Z-Score
        cot_processed = cot_processed.sort_values("date").reset_index(drop=True)
        save_csv(cot_processed, "data/processed/btc_cot_processed.csv")

    # COT ETH
    print("Скачиваем и обрабатываем COT данные для ETH...")
    cot_eth_raw = fetch_cot_raw('ETH')
    if not cot_eth_raw.empty:
        save_csv(cot_eth_raw, "data/raw/eth_cot_raw.csv")
        cot_eth_processed = preprocess(cot_eth_raw)
        cot_eth_processed = build_indicators(cot_eth_processed)
        cot_eth_processed = calculate_z_score(cot_eth_processed)  # Добавлен Z-Score
        cot_eth_processed = cot_eth_processed.sort_values("date").reset_index(drop=True)
        save_csv(cot_eth_processed, "data/processed/eth_cot_processed.csv")
        print("Все данные успешно обновлены.")
    else:
        print("Не удалось загрузить COT данные.")

if __name__ == "__main__":
    main()