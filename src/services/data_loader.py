from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from src.config.settings import get_settings


@lru_cache(maxsize=None)
def load_dataset(name: str, tz_aware: bool = True) -> Optional[pd.DataFrame]:
    s = get_settings()
    rel_path = s.files.get(name)
    if not rel_path:
        return None

    path = Path(s.data_dir) / rel_path
    if not path.exists():
        return None

    df = pd.read_csv(path)
    if "date" in df.columns:
        dt_series = pd.to_datetime(df["date"], utc=tz_aware, errors="coerce")
        if tz_aware:
            df["date"] = dt_series.dt.tz_localize(None)
        else:
            df["date"] = dt_series
    return df


def all_data_loaded(dfs: Dict[str, Optional[pd.DataFrame]]) -> bool:
    return all(df is not None and not df.empty for df in dfs.values())


def filter_df(df: Optional[pd.DataFrame], start, end) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if "date" not in df.columns:
        return pd.DataFrame()

    dt_col = df["date"]
    if not pd.api.types.is_datetime64_any_dtype(dt_col):
        # OPTIMIZED: не делаем лишний df.copy(); преобразуем только колонку, как и раньше.
        dt_col = pd.to_datetime(dt_col, errors="coerce")

    # OPTIMIZED: эквивалентно dt.date.between(start,end), но без создания массива python-date.
    # Для tz-aware (если вдруг прилетит) — поведение близко к dt.date (сначала "снимаем" tz).
    if pd.api.types.is_datetime64tz_dtype(dt_col):
        dt_col = dt_col.dt.tz_localize(None)

    dt_norm = dt_col.dt.normalize()
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()

    mask = dt_norm.between(start_ts, end_ts, inclusive="both")
    out = df.loc[mask].copy()  # OPTIMIZED: копируем только отфильтрованную часть
    if out.empty:
        return out.reset_index(drop=True)

    if out["date"] is not dt_col:
        # Если мы создавали dt_col отдельно (не dtype datetime), синхронизируем столбец "date"
        out["date"] = dt_col.loc[mask].values
    return out.reset_index(drop=True)