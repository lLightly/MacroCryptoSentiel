# MacroCryptoSentinel/src/analytics/statistics.py
import pandas as pd

def add_vix_deviation_indicators(
    df: pd.DataFrame,
    window: int = 252,
    price_col: str = "close"
) -> pd.DataFrame:
    """
    Добавляет индикаторы отклонения VIX в % от скользящего среднего.
    Логика точно по требованию: статические горизонтальные уровни на основе всей серии отклонений.
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])

    close = df[price_col]

    # Скользящее среднее
    df["rolling_mean"] = close.rolling(window=window).mean()

    # Процентное отклонение
    df["deviation_pct"] = (close / df["rolling_mean"] - 1) * 100

    # Удаляем строки до полного окна
    df = df.dropna(subset=["rolling_mean"]).reset_index(drop=True)

    return df


def get_deviation_levels(df: pd.DataFrame, col: str = "deviation_pct", sigma_levels: list = None) -> dict:
    """
    Вычисляет статические уровни для графика:
    - mean_dev: среднее отклонение (красная линия)
    - +1σ, +2σ (оранжевые)
    - -1σ, -2σ (зелёные)
    """
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