# finance_api.py (обновленный: добавлены fetch_nasdaq, fetch_dxy, fetch_us10y)
import yfinance as yf
import pandas as pd

def fetch_vix(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("^VIX")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные VIX")

    df = df.reset_index()
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


def fetch_btc(start: str = "2014-09-17", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("BTC-USD")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные BTC")

    df = df.reset_index()
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


def fetch_eth(start: str = "2015-08-07", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("ETH-USD")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные ETH")

    df = df.reset_index()
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


def fetch_spx(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("^GSPC")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные S&P 500")

    df = df.reset_index()
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

def fetch_nasdaq(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("^IXIC")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные Nasdaq")

    df = df.reset_index()
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

def fetch_dxy(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("DX-Y.NYB")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные DXY")

    df = df.reset_index()
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

def fetch_us10y(start: str = "2000-01-01", interval: str = "1d") -> pd.DataFrame:
    ticker_obj = yf.Ticker("^TNX")
    df = ticker_obj.history(start=start, interval=interval)

    if df.empty:
        raise RuntimeError("Не удалось загрузить данные US10Y")

    df = df.reset_index()
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