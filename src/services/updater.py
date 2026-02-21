from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict

import pandas as pd

from src.analytics.indicators import build_indicators
from src.analytics.statistics import add_vix_deviation_indicators, calculate_z_score
from src.config.settings import get_settings
from src.data_fetchers import finance_api
from src.data_fetchers.cot_parser import fetch_cot_raw, preprocess
from src.utils.helpers import save_csv


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def _update_price(name: str, fetch_fn: Callable[[], pd.DataFrame], proc_dir: str) -> None:
    df = fetch_fn()
    save_csv(df, f"{proc_dir}/{name}_price.csv")


def _update_cot(asset: str, raw_dir: str, proc_dir: str) -> None:
    cot_raw = fetch_cot_raw(asset)
    if cot_raw.empty:
        return

    save_csv(cot_raw, f"{raw_dir}/{asset.lower()}_cot_raw.csv")

    cot = preprocess(cot_raw)
    cot = build_indicators(cot)
    cot = calculate_z_score(cot)

    save_csv(cot.sort_values("date"), f"{proc_dir}/{asset.lower()}_cot_processed.csv")


def update_all_data() -> None:
    s = get_settings()
    raw_dir = "data/raw"
    proc_dir = str(Path(s.data_dir))

    _ensure_dirs(raw_dir, proc_dir)

    vix_raw = finance_api.fetch_vix()
    save_csv(vix_raw, f"{raw_dir}/vix.csv")
    vix = add_vix_deviation_indicators(vix_raw, window=252)
    save_csv(vix, f"{proc_dir}/vix_processed.csv")

    price_fetchers: Dict[str, Callable] = {
        "btc": finance_api.fetch_btc,
        "eth": finance_api.fetch_eth,
        "spx": finance_api.fetch_spx,
        "nasdaq": finance_api.fetch_nasdaq,
        "dxy": finance_api.fetch_dxy,
        "us10y": finance_api.fetch_us10y,
    }
    for name, fn in price_fetchers.items():
        _update_price(name, fn, proc_dir)

    _update_cot("BTC", raw_dir, proc_dir)
    _update_cot("ETH", raw_dir, proc_dir)