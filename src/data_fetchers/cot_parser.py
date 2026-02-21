from __future__ import annotations

from typing import Dict, List

import pandas as pd
import requests

BASE_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
LIMIT = 50000

MARKETS: Dict[str, str] = {
    "BTC": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
    "ETH": "ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE",
}


def fetch_cot_raw(asset: str = "BTC") -> pd.DataFrame:
    market = MARKETS.get(asset.upper())
    if not market:
        raise ValueError(f"Unknown asset: {asset}")

    offset = 0
    data: List[dict] = []
    while True:
        params = {"$limit": LIMIT, "$offset": offset, "$where": f"market_and_exchange_names='{market}'"}
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        data.extend(batch)
        offset += LIMIT

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
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    df = df.sort_values("date").reset_index(drop=True)
    df["Comm_Net"] = df["comm_positions_long_all"] - df["comm_positions_short_all"]
    df["Large_Specs_Net"] = df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    df["Small_Traders_Net"] = df["nonrept_positions_long_all"] - df["nonrept_positions_short_all"]
    return df