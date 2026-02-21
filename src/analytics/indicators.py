from __future__ import annotations

import pandas as pd


def _cot_index(series: pd.Series, window: int = 26) -> pd.Series:
    s = pd.to_numeric(series, errors='coerce')          # extra safety
    rolling = s.rolling(window=window, min_periods=1)
    index = (s - rolling.min()) / (rolling.max() - rolling.min()) * 100
    return index


def build_indicators(df: pd.DataFrame, window: int = 26) -> pd.DataFrame:
    df = df.copy()
    df["COT_Index_Comm_26w"] = _cot_index(df["Comm_Net"], window=window).round(2)
    df["COT_Index_Large_26w"] = _cot_index(df["Large_Specs_Net"], window=window).round(2)
    df["COT_Index_Large_Inverted_26w"] = (100 - df["COT_Index_Large_26w"]).round(2)
    return df