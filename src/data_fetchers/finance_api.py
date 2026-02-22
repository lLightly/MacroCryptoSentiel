from __future__ import annotations

from functools import lru_cache

import pandas as pd
import yfinance as yf

from src.config.settings import get_settings


@lru_cache(maxsize=None)
def _fetch_yahoo(ticker: str, start: str, interval: str = "1d") -> pd.DataFrame:
    df = yf.Ticker(ticker).history(start=start, interval=interval)
    if df.empty:
        raise RuntimeError(f"Failed to load {ticker} from Yahoo Finance")

    df = (
        df.reset_index()
        .rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )[
            ["date", "open", "high", "low", "close", "volume"]
        ]
    )
    return df


def fetch_vix(start: str = "2019-05-12", interval: str = "1d") -> pd.DataFrame:
    return _fetch_yahoo("^VIX", start, interval)


def fetch_btc(start: str = "2020-05-12", interval: str = "1d") -> pd.DataFrame:
    s = get_settings()
    return _fetch_yahoo("BTC-USD", start or s.raw["assets"]["btc"]["price_start"], interval)


def fetch_eth(start: str = "2023-03-28", interval: str = "1d") -> pd.DataFrame:
    s = get_settings()
    return _fetch_yahoo("ETH-USD", start or s.raw["assets"]["eth"]["price_start"], interval)


def fetch_spx(start: str = "2020-05-12", interval: str = "1d") -> pd.DataFrame:
    return _fetch_yahoo("^GSPC", start, interval)


def fetch_nasdaq(start: str = "2020-05-12", interval: str = "1d") -> pd.DataFrame:
    return _fetch_yahoo("^IXIC", start, interval)


def fetch_dxy(start: str = "2020-05-12", interval: str = "1d") -> pd.DataFrame:
    return _fetch_yahoo("DX-Y.NYB", start, interval)


def fetch_us10y(start: str = "2020-05-12", interval: str = "1d") -> pd.DataFrame:
    return _fetch_yahoo("^TNX", start, interval)