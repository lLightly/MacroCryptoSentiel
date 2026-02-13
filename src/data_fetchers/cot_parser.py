import requests
import pandas as pd

BASE_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
BTC_MARKET = "BITCOIN - CHICAGO MERCANTILE EXCHANGE"
LIMIT = 50000

def fetch_cot_raw() -> pd.DataFrame:
    print("Fetching Legacy COT data for BTC...")
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
    return pd.DataFrame(data)


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df = df.rename(columns={"report_date_as_yyyy_mm_dd": "date"})
    df["date"] = pd.to_datetime(df["date"])

    num_cols = [
        "open_interest_all",
        "comm_positions_long_all",
        "comm_positions_short_all",
        "noncomm_positions_long_all",
        "noncomm_positions_short_all",
        "nonrept_positions_long_all",
        "nonrept_positions_short_all",
    ]

    # Критически важно: fillna(0) после to_numeric, чтобы избежать NaN и KeyError
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    df = df.sort_values("date").reset_index(drop=True)

    df["Comm_Net"] = df["comm_positions_long_all"] - df["comm_positions_short_all"]
    df["Large_Specs_Net"] = (
        df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    )
    df["Small_Traders_Net"] = (
        df["nonrept_positions_long_all"] - df["nonrept_positions_short_all"]
    )

    return df