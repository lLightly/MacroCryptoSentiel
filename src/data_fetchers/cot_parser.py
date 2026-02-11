# MacroCryptoSentinel/src/data_fetchers/cot_parser.py
import requests
import pandas as pd

BASE_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
BTC_MARKET = "BITCOIN - CHICAGO MERCANTILE EXCHANGE"
LIMIT = 50000


def fetch_all():
    print("Fetching Legacy COT data...")
    offset = 0
    data = []

    while True:
        params = {
            "$limit": LIMIT,
            "$offset": offset,
            "$where": f"market_and_exchange_names='{BTC_MARKET}'"
        }

        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()

        if not batch:
            break

        data.extend(batch)
        offset += LIMIT

    print(f"Total records fetched: {len(data)}")

    # Сохранение в data/raw/ (согласно структуре)
    raw_df = pd.DataFrame(data)
    raw_df.to_csv("data/raw/btc_cot_raw.csv", index=False)
    print("Saved raw data: data/raw/btc_cot_raw.csv")

    return raw_df


def preprocess(df):
    df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(
        df["report_date_as_yyyy_mm_dd"]
    )

    num_cols = [
        "open_interest_all",
        "comm_positions_long_all",
        "comm_positions_short_all",
        "noncomm_positions_long_all",
        "noncomm_positions_short_all",
        "nonrept_positions_long_all",
        "nonrept_positions_short_all",
    ]

    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.sort_values("report_date_as_yyyy_mm_dd").reset_index(drop=True)

    df["Comm_Net"] = df["comm_positions_long_all"] - df["comm_positions_short_all"]

    df["Large_Specs_Net"] = (
        df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    )

    df["Small_Traders_Net"] = (
        df["nonrept_positions_long_all"] - df["nonrept_positions_short_all"]
    )

    return df