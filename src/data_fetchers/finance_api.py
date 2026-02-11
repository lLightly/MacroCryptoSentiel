# MacroCryptoSentinel/src/data_fetchers/finance_api.py
import yfinance as yf
import requests
import pandas as pd

# ========================
# VIX через yfinance (используем Ticker.history для избежания MultiIndex колонок)
# ========================
def fetch_vix(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("^VIX")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные VIX")

    df = df.reset_index()
    # History возвращает: Date, Open, High, Low, Close, Volume, Dividends, Stock Splits
    # Для VIX Dividends/Splits = 0, Close ≈ Adj Close
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

    df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    }, inplace=True)

    return df

# ========================
# BTCUSDT через Binance API (без изменений)
# ========================
def fetch_btcusdt_spot(interval: str = "1d", limit: int = 1000) -> pd.DataFrame:
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])

    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    return df

# ========================
# Унифицированный интерфейс
# ========================
def fetch_all_market_data():
    vix = fetch_vix()
    btc = fetch_btcusdt_spot()
    return {"vix": vix, "btc": btc}