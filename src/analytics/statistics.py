# statistics.py (обновленный: добавлена calculate_z_score для COT)
import pandas as pd

def add_vix_deviation_indicators(
    df: pd.DataFrame,
    window: int = 252,
    price_col: str = "close"
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])

    close = df[price_col]

    df["rolling_mean"] = close.rolling(window=window).mean()

    df["deviation_pct"] = (close / df["rolling_mean"] - 1) * 100

    df = df.dropna(subset=["rolling_mean"]).reset_index(drop=True)

    return df


def get_deviation_levels(df: pd.DataFrame, col: str = "deviation_pct", sigma_levels: list = None) -> dict:
    if sigma_levels is None:
        sigma_levels = [1, 2]

    series = df[col]

    mean_dev = series.mean()
    std_dev = series.std()

    levels = {
        "mean": mean_dev,
    }

    for level in sigma_levels:
        levels[f"+{level}σ"] = mean_dev + level * std_dev
        levels[f"-{level}σ"] = mean_dev - level * std_dev

    return levels

def calculate_z_score(df: pd.DataFrame, column: str = "Large_Specs_Net", window: int = 104) -> pd.DataFrame:  # 104 weeks = 2 years
    """
    Добавляет Z-Score для указанной колонки (COT weekly data).
    """
    df = df.copy()
    rolling_mean = df[column].rolling(window).mean()
    rolling_std = df[column].rolling(window).std()
    df['Z_Score_Large'] = (df[column] - rolling_mean) / rolling_std
    df = df.dropna(subset=['Z_Score_Large']).reset_index(drop=True)
    return df